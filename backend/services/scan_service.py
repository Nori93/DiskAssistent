"""
Background scanning service that runs in a thread pool.
Handles long-running scans without blocking the API.
"""
from __future__ import annotations

import contextlib
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ai.categorizer import categorize
from backend.config import logger
from backend.services.scanner import scan_directory
from database.models import FileGroup, FileRecord, ScanJob, SessionLocal

# Single-worker executor so scans are serialized and don't overload disk I/O
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="scanner")

# Active scan job id → Future mapping
_active_jobs: dict[int, object] = {}
_lock = threading.Lock()


def _upsert_file_batch(db, values: list[dict]) -> None:
    """Bulk upsert file records — insert new, update metadata for existing.
    Category is preserved when category_overridden is True.
    Retries on SQLITE_BUSY / SQLITE_LOCKED for up to ~60 seconds.
    """
    import time

    from sqlalchemy import case as sa_case
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    stmt = sqlite_insert(FileRecord.__table__).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["full_path"],
        set_={
            "size_bytes":  stmt.excluded.size_bytes,
            "modified_at": stmt.excluded.modified_at,
            "scanned_at":  stmt.excluded.scanned_at,
            "is_missing":  False,
            "ai_category": sa_case(
                (FileRecord.__table__.c.category_overridden.is_(False), stmt.excluded.ai_category),
                else_=FileRecord.__table__.c.ai_category,
            ),
            "category": sa_case(
                (FileRecord.__table__.c.category_overridden.is_(False), stmt.excluded.category),
                else_=FileRecord.__table__.c.category,
            ),
        },
    )

    max_attempts = 120   # 120 × 0.5 s = 60 s of retry headroom
    for attempt in range(max_attempts):
        try:
            db.execute(stmt)
            return
        except Exception as exc:
            err = str(exc).lower()
            if ("locked" in err or "busy" in err) and attempt < max_attempts - 1:
                logger.debug(
                    "_upsert_file_batch: DB locked (attempt %d/%d), retrying in 0.5 s…",
                    attempt + 1, max_attempts,
                )
                with contextlib.suppress(Exception):
                    db.rollback()
                time.sleep(0.5)
                continue
            raise


def start_scan(root_path: str) -> int:
    """
    Create a ScanJob record and submit the scan to the background executor.
    Returns the job ID.
    """
    db = SessionLocal()
    try:
        job = ScanJob(root_path=root_path, status="pending")
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    future = _executor.submit(_run_scan, job_id, root_path)
    with _lock:
        _active_jobs[job_id] = future

    logger.info("Scan job %d submitted for: %s", job_id, root_path)
    return job_id


def get_job_status(job_id: int) -> dict | None:
    db = SessionLocal()
    try:
        job = db.get(ScanJob, job_id)
        return job.to_dict() if job else None
    finally:
        db.close()


def get_active_scan() -> dict | None:
    """
    Return the most recent job that is still running or pending, or None.
    Used by the frontend on page load to reconnect to an in-progress scan.
    """
    db = SessionLocal()
    try:
        job = (
            db.query(ScanJob)
            .filter(ScanJob.status.in_(["running", "pending"]))
            .order_by(ScanJob.id.desc())
            .first()
        )
        return job.to_dict() if job else None
    finally:
        db.close()


def resume_interrupted_scans() -> None:
    """
    Called once at application startup.
    Any job left in 'running' or 'pending' state (e.g. after a server restart)
    is re-submitted to the executor so it actually runs to completion.
    """
    db = SessionLocal()
    try:
        stale = (
            db.query(ScanJob)
            .filter(ScanJob.status.in_(["running", "pending"]))
            .all()
        )
        if not stale:
            return
        for job in stale:
            # Reset progress counters so the re-run starts clean
            job.status      = "pending"
            job.processed   = 0
            job.total_files = 0
            job.error_msg   = ""
            job.current_disk  = ""
            job.disk_progress = "{}"
        db.commit()

        for job in stale:
            root = job.root_path
            job_id = job.id
            # Detect whether this was a rescan-all job (multiple paths separated by ;)
            if ";" in root:
                disks = [d for d in root.split(";") if d]
                future = _executor.submit(_run_rescan_all, job_id, disks)
                logger.info("Resumed rescan-all job %d for disks: %s", job_id, disks)
            else:
                future = _executor.submit(_run_scan, job_id, root)
                logger.info("Resumed scan job %d for: %s", job_id, root)
            with _lock:
                _active_jobs[job_id] = future
    finally:
        db.close()


def start_rescan_all() -> int:
    """
    Clear the entire database (files, groups, old scan jobs) and start a
    fresh scan of every detected disk/mount point.
    Returns the single ScanJob id used to track progress.
    """
    from backend.services.scanner import get_available_disks

    disks = [d["path"] for d in get_available_disks()]
    if not disks:
        raise ValueError("No disks detected.")

    db = SessionLocal()
    try:
        # Wipe all indexed data so we start clean
        db.query(FileRecord).delete()
        db.query(FileGroup).delete()
        db.query(ScanJob).delete()
        db.commit()

        # One job whose root_path is a CSV of all disks
        job = ScanJob(root_path=";".join(disks), status="pending")
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    future = _executor.submit(_run_rescan_all, job_id, disks)
    with _lock:
        _active_jobs[job_id] = future

    logger.info("Rescan-all job %d submitted for disks: %s", job_id, disks)
    return job_id


# ── Worker ────────────────────────────────────────────────────────────────────

def _run_scan(job_id: int, root_path: str):
    """Run in worker thread."""
    db = SessionLocal()
    try:
        job = db.get(ScanJob, job_id)
        if not job:
            return
        job.status     = "running"
        job.started_at = datetime.datetime.utcnow()
        db.commit()

        # --- Phase 1: count files for progress reporting ---
        logger.info("[Job %d] Counting files in %s …", job_id, root_path)
        total = sum(1 for _ in scan_directory(root_path))
        job.total_files = total
        db.commit()

        # --- Phase 2: index files ---
        logger.info("[Job %d] Indexing %d files …", job_id, total)
        processed = 0

        for file_meta in scan_directory(root_path):
            fp = file_meta["full_path"]

            # Upsert: update if existing, insert if new
            existing = db.query(FileRecord).filter(
                FileRecord.full_path == fp
            ).first()

            cat = str(categorize(fp))   # coerce np.str_ → str

            if existing:
                existing.size_bytes   = file_meta["size_bytes"]
                existing.modified_at  = file_meta["modified_at"]
                existing.is_missing   = False
                if not existing.category_overridden:
                    existing.ai_category = cat
                    existing.category    = cat
            else:
                rec = FileRecord(
                    name        = file_meta["name"],
                    full_path   = fp,
                    parent_dir  = file_meta["parent_dir"],
                    extension   = file_meta["extension"],
                    size_bytes  = file_meta["size_bytes"],
                    created_at  = file_meta["created_at"],
                    modified_at = file_meta["modified_at"],
                    ai_category = cat,
                    category    = cat,
                )
                db.add(rec)

            processed += 1
            if processed % 500 == 0:
                db.commit()
                job.processed = processed
                db.commit()
                logger.debug("[Job %d] Processed %d/%d", job_id, processed, total)

        job.processed = processed
        db.commit()

        # --- Phase 3: detect groups ---
        logger.info("[Job %d] Detecting groups …", job_id)
        _index_groups(db, root_path)

        # --- Phase 4: mark missing files ---
        _mark_missing(db, root_path)

        job.status      = "done"
        job.finished_at = datetime.datetime.utcnow()
        db.commit()
        logger.info("[Job %d] Scan complete. %d files indexed.", job_id, processed)

    except Exception as exc:
        logger.exception("[Job %d] Scan failed: %s", job_id, exc)
        job = db.get(ScanJob, job_id)
        if job:
            job.status    = "error"
            job.error_msg = str(exc)
            db.commit()
    finally:
        db.close()
        with _lock:
            _active_jobs.pop(job_id, None)


def _run_rescan_all(job_id: int, disks: list[str]):
    """
    Worker that scans every disk sequentially, aggregating progress into one
    ScanJob record so the frontend can poll a single job_id.
    Per-disk progress is written to job.disk_progress (JSON).
    """
    import json

    db = SessionLocal()
    try:
        job = db.get(ScanJob, job_id)
        if not job:
            return
        job.status     = "running"
        job.started_at = datetime.datetime.utcnow()
        db.commit()

        # Phase 1 — count total files per disk (use seen-path dedup to match indexing)
        logger.info("[Job %d] Counting files on all disks …", job_id)
        disk_totals: dict[str, int] = {}
        for disk in disks:
            try:
                seen_count: set[str] = set()
                n = 0
                for fm in scan_directory(disk):
                    fp = fm["full_path"]
                    if fp not in seen_count:
                        seen_count.add(fp)
                        n += 1
            except Exception:
                n = 0
            disk_totals[disk] = n

        total = sum(disk_totals.values())
        job.total_files = total

        # Initialise per-disk progress map
        dp: dict[str, dict] = {
            d: {"total": disk_totals[d], "processed": 0, "status": "pending"}
            for d in disks
        }
        job.disk_progress = json.dumps(dp)
        db.commit()

        # Phase 2 — index every disk
        processed = 0
        for disk in disks:
            logger.info("[Job %d] Indexing %s …", job_id, disk)
            job.current_disk = disk
            dp[disk]["status"] = "scanning"
            job.disk_progress = json.dumps(dp)
            db.commit()

            disk_processed = 0
            seen_paths:  set[str]  = set()   # guard against duplicate paths (junctions, symlinks)
            batch_values: list[dict] = []
            try:
                for file_meta in scan_directory(disk):
                    fp = file_meta["full_path"]
                    if fp in seen_paths:
                        continue
                    seen_paths.add(fp)
                    cat = str(categorize(fp))   # coerce np.str_ → str

                    batch_values.append({
                        "name":               file_meta["name"],
                        "full_path":          fp,
                        "parent_dir":         file_meta["parent_dir"],
                        "extension":          file_meta["extension"],
                        "size_bytes":         file_meta["size_bytes"],
                        "created_at":         file_meta["created_at"],
                        "modified_at":        file_meta["modified_at"],
                        "scanned_at":         datetime.datetime.utcnow(),
                        "ai_category":        cat,
                        "category":           cat,
                        "category_overridden": False,
                        "tags":               "",
                        "description":        "",
                        "thumbnail_path":     "",
                        "group_id":           None,
                        "is_missing":         False,
                    })
                    processed      += 1
                    disk_processed += 1

                    if len(batch_values) >= 100:
                        try:
                            _upsert_file_batch(db, batch_values)
                            job.processed = processed
                            dp[disk]["processed"] = disk_processed
                            job.disk_progress = json.dumps(dp)
                            db.commit()
                        except Exception as commit_exc:
                            logger.warning("[Job %d] Batch upsert error, rolling back: %s", job_id, commit_exc)
                            db.rollback()
                        batch_values.clear()

                if batch_values:
                    try:
                        _upsert_file_batch(db, batch_values)
                        db.commit()
                    except Exception as commit_exc:
                        logger.warning("[Job %d] Final batch upsert error, rolling back: %s", job_id, commit_exc)
                        db.rollback()
                    batch_values.clear()

            except Exception as exc:
                logger.warning("[Job %d] Error scanning %s: %s", job_id, disk, exc)
                db.rollback()
                dp[disk]["status"] = "error"
            else:
                dp[disk]["status"] = "done"

            dp[disk]["processed"] = disk_processed
            job.processed     = processed
            job.disk_progress = json.dumps(dp)
            db.commit()

        job.current_disk = "__finalizing__"
        # Normalize processed to total so the bar shows 100% during group detection
        job.processed = job.total_files
        db.commit()

        # Phase 3 — detect groups for every disk (fast SQL only, no icon extraction)
        for disk in disks:
            try:
                _index_groups(db, disk, extract_icons=False)
            except Exception as exc:
                logger.warning("[Job %d] Group detection failed for %s: %s", job_id, disk, exc)

        job.status      = "done"
        job.current_disk = ""
        job.finished_at = datetime.datetime.utcnow()
        db.commit()
        logger.info("[Job %d] Rescan-all complete. %d files indexed.", job_id, processed)

        # Phase 4 — icon extraction in background (job already marked done)
        for disk in disks:
            try:
                _extract_icons_for_disk(db, disk)
            except Exception as exc:
                logger.warning("[Job %d] Icon extraction failed for %s: %s", job_id, disk, exc)

    except Exception as exc:
        logger.exception("[Job %d] Rescan-all failed: %s", job_id, exc)
        job = db.get(ScanJob, job_id)
        if job:
            job.status    = "error"
            job.error_msg = str(exc)
            db.commit()
    finally:
        db.close()
        with _lock:
            _active_jobs.pop(job_id, None)


def _index_groups(db, root_path: str, extract_icons: bool = True):
    """Build FileGroup records from DB data (no disk walk needed — files are
    already committed when this is called).
    Uses regroup_from_db which runs pure SQL — fast even for full-disk scans.
    When extract_icons=False, skips PowerShell icon extraction (used during
    rescan-all so the job can finish quickly).
    """
    import os

    from backend.services.grouper import regroup_from_db
    from backend.services.icon_service import extract_group_icon, pick_best_exe

    groups_data = regroup_from_db(db, root_path)
    logger.info("_index_groups: %d groups found for %s", len(groups_data), root_path)

    for gd in groups_data:
        existing = db.query(FileGroup).filter(
            FileGroup.root_path == gd["root_path"]
        ).first()
        if not existing:
            grp = FileGroup(
                name        = gd["name"],
                root_path   = gd["root_path"],
                category    = gd["category"],
                description = gd["description"],
            )
            db.add(grp)
            db.flush()   # get grp.id
        else:
            grp = existing
            existing.category       = gd["category"]
            existing.description    = gd["description"]
            existing.file_tree_json = None  # invalidate cached tree

        # Tag ALL files recursively under this group root
        grp_root    = gd["root_path"]
        sep         = os.sep
        clean_grp   = grp_root.rstrip(sep) or sep
        like_prefix = clean_grp + sep + "%"
        db.query(FileRecord).filter(
            (FileRecord.parent_dir == grp_root) |
            (FileRecord.parent_dir == clean_grp) |
            FileRecord.parent_dir.like(like_prefix)
        ).update({"group_id": grp.id}, synchronize_session=False)

        # Extract exe icon if this is a Games group and we don't have one yet
        if extract_icons and (gd.get("category") == "Games") and not grp.thumbnail_path:
            db.flush()  # ensure group_id is assigned on FileRecords
            exe = pick_best_exe(db, grp.id, grp_root)
            if exe:
                url = extract_group_icon(grp.id, exe)
                if url:
                    grp.thumbnail_path = url

    db.commit()


def _extract_icons_for_disk(db, root_path: str):
    """Run icon extraction for all Games groups under root_path that lack a thumbnail.
    Called after the scan job is already marked done so it doesn't block the UI.
    """
    from backend.services.icon_service import extract_group_icon, pick_best_exe

    groups = db.query(FileGroup).filter(
        FileGroup.category == "Games",
        FileGroup.root_path.like(root_path.rstrip("\\\"/") + "%"),
        FileGroup.thumbnail_path.is_(None) | (FileGroup.thumbnail_path == ""),
    ).all()
    for grp in groups:
        try:
            exe = pick_best_exe(db, grp.id, grp.root_path)
            if exe:
                url = extract_group_icon(grp.id, exe)
                if url:
                    grp.thumbnail_path = url
                    db.commit()
        except Exception as exc:
            logger.debug("_extract_icons_for_disk: group %d failed: %s", grp.id, exc)


def _mark_missing(db, root_path: str):
    """
    Mark FileRecords under root_path as missing if the file is gone from disk.
    """
    import os
    sep = os.sep
    clean_root = root_path.rstrip(sep) or sep
    like_prefix = clean_root + sep + "%"
    records = db.query(FileRecord).filter(
        (FileRecord.parent_dir == root_path) |
        (FileRecord.parent_dir == clean_root) |
        FileRecord.parent_dir.like(like_prefix)
    ).all()
    for rec in records:
        if not Path(rec.full_path).exists():
            rec.is_missing = True
    db.commit()
