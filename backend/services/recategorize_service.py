"""
Background recategorize service.
Runs categorization in a worker thread and tracks progress in RecategorizeJob.
"""

from __future__ import annotations

import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from backend.config import logger
from database.models import FileRecord, RecategorizeJob, SessionLocal

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="recategorize")
_active_jobs: dict[int, object] = {}
_lock = threading.Lock()


def start_recategorize(
    scope: str,
    only_auto: bool,
    category: str | None,
    group_id: int | None,
    regroup: bool = True,
    skip_categorize: bool = False,
) -> int:
    """Create a RecategorizeJob and submit it to the background executor."""
    db = SessionLocal()
    try:
        job = RecategorizeJob(scope=scope, status="pending")
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    future = _executor.submit(
        _run_recategorize, job_id, only_auto, category, group_id, regroup, skip_categorize
    )
    with _lock:
        _active_jobs[job_id] = future

    logger.info(
        "Recategorize job %d submitted. scope=%s regroup=%s skip_cat=%s",
        job_id,
        scope,
        regroup,
        skip_categorize,
    )
    return job_id


def get_recategorize_status(job_id: int) -> dict | None:
    db = SessionLocal()
    try:
        job = db.get(RecategorizeJob, job_id)
        return job.to_dict() if job else None
    finally:
        db.close()


def get_recategorize_history(limit: int = 50) -> list[dict]:
    db = SessionLocal()
    try:
        jobs = db.query(RecategorizeJob).order_by(RecategorizeJob.id.desc()).limit(limit).all()
        return [j.to_dict() for j in jobs]
    finally:
        db.close()


def _run_recategorize(
    job_id: int,
    only_auto: bool,
    category: str | None,
    group_id: int | None,
    regroup: bool = True,
    skip_categorize: bool = False,
):
    """Worker: runs in the thread pool."""
    db = SessionLocal()
    try:
        job = db.get(RecategorizeJob, job_id)
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.datetime.utcnow()
        db.commit()

        # ── Phase 1: recategorize (skipped in regroup-only mode) ───────
        if not skip_categorize:
            from ai.categorizer import categorize

            q = db.query(FileRecord)
            if only_auto:
                q = q.filter(FileRecord.category_overridden == False)  # noqa: E712
            if category:
                q = q.filter(FileRecord.category == category)
            if group_id is not None:
                q = q.filter(FileRecord.group_id == group_id)

            records = q.all()
            total = len(records)
            job.total = total
            db.commit()

            changed = 0
            for i, rec in enumerate(records, 1):
                new_cat = str(categorize(rec.full_path))
                if new_cat != rec.ai_category or new_cat != rec.category:
                    rec.ai_category = new_cat
                    rec.category = new_cat
                    changed += 1

                if i % 200 == 0:
                    job.processed = i
                    job.changed = changed
                    db.commit()
                    logger.debug("[RecatJob %d] %d/%d processed", job_id, i, total)

            job.processed = total
            job.changed = changed
            db.commit()
            logger.info("[RecatJob %d] Recategorize done. %d/%d changed.", job_id, changed, total)
        else:
            # Regroup-only: set totals to 0 (nothing to categorize)
            job.total = 0
            job.processed = 0
            job.changed = 0
            db.commit()

        # ── Phase 2: regroup from DB (no disk access) ──────────────────
        if regroup:
            _regroup_phase(db, job_id)

        job.status = "done"
        job.finished_at = datetime.datetime.utcnow()
        db.commit()
        logger.info("[RecatJob %d] All done.", job_id)

    except Exception as exc:
        logger.exception("[RecatJob %d] Failed: %s", job_id, exc)
        db_err = SessionLocal()
        try:
            j = db_err.get(RecategorizeJob, job_id)
            if j:
                j.status = "error"
                j.error_msg = str(exc)
                db_err.commit()
        finally:
            db_err.close()
    finally:
        db.close()
        with _lock:
            _active_jobs.pop(job_id, None)


def _regroup_phase(db, job_id: int) -> None:
    """
    Rebuild all FileGroup records and update FileRecord.group_id
    entirely from the database — no disk scanning.
    """
    import os

    from backend.services.grouper import regroup_from_db
    from database.models import FileGroup, ScanJob

    # Collect scan roots from completed (or partially-complete) scan jobs
    scan_roots: list[str] = []
    done_jobs = db.query(ScanJob).filter(ScanJob.status.in_(["done", "error"])).all()
    seen: set[str] = set()
    for sj in done_jobs:
        for rp in sj.root_path.split(";"):
            rp = rp.strip()
            if rp and rp not in seen:
                seen.add(rp)
                scan_roots.append(rp)

    # Fallback: derive roots from indexed file data when no scan jobs are recorded
    if not scan_roots:
        rows = db.query(FileRecord.parent_dir).distinct().limit(50000).all()
        # Find the shortest (topmost) unique paths — these are the scan roots
        all_dirs = sorted({r[0] for r in rows if r[0]}, key=len)
        for d in all_dirs:
            if not any(d.startswith(r) for r in seen):
                seen.add(d)
                scan_roots.append(d)
        # Keep only the topmost (shortest path) per drive/prefix
        scan_roots = _dedupe_roots(scan_roots)

    if not scan_roots:
        logger.info("[RecatJob %d] No scan roots found; skipping regroup.", job_id)
        return

    logger.info("[RecatJob %d] Regrouping from DB for roots: %s", job_id, scan_roots)

    # Clear all existing groups and reset group_id assignments
    db.query(FileRecord).update({"group_id": None}, synchronize_session="fetch")
    db.query(FileGroup).delete()
    db.commit()

    total_groups = 0
    for root_path in scan_roots:
        try:
            groups_data = regroup_from_db(db, root_path)
        except Exception as exc:
            logger.warning(
                "[RecatJob %d] regroup_from_db failed for %s: %s", job_id, root_path, exc
            )
            continue

        sep = os.sep
        for gd in groups_data:
            grp = FileGroup(
                name=gd["name"],
                root_path=gd["root_path"],
                category=gd["category"],
                description=gd["description"],
            )
            db.add(grp)
            db.flush()

            grp_root = gd["root_path"]
            clean_grp = grp_root.rstrip(sep) or sep
            like_prefix = clean_grp + sep + "%"
            db.query(FileRecord).filter(
                (FileRecord.parent_dir == grp_root)
                | (FileRecord.parent_dir == clean_grp)
                | FileRecord.parent_dir.like(like_prefix)
            ).update({"group_id": grp.id}, synchronize_session=False)
            total_groups += 1

        db.commit()

    logger.info("[RecatJob %d] Regroup done. %d groups created.", job_id, total_groups)


def _dedupe_roots(paths: list[str]) -> list[str]:
    """Keep only the topmost paths — remove any path that is a sub-path of another."""
    import os

    paths = sorted(paths, key=len)
    result: list[str] = []
    for p in paths:
        p_norm = p.rstrip(os.sep) + os.sep
        if not any(p_norm.startswith(r.rstrip(os.sep) + os.sep) and p != r for r in result):
            result.append(p)
    return result
