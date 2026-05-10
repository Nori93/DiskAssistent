"""
Archive service: compress game groups to a zip file and restore them later.

Each operation runs in a daemon thread so the API never blocks.
Job progress is tracked in-memory (keyed by group_id).
"""

from __future__ import annotations

import datetime
import json
import re
import shutil
import threading
import zipfile
from pathlib import Path

from config import logger
from diskassistent_db.models import ArchiveJob, FileGroup, FileRecord, SessionLocal
from services import dedup_service, settings_service

# â”€â”€ In-memory job registry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# { group_id: {"status": "idle|running|done|error", "progress": 0-100, "error": str|None} }
_jobs: dict[int, dict] = {}
_lock = threading.Lock()


def _set_job(group_id: int, data: dict) -> None:
    with _lock:
        _jobs[group_id] = data


def get_status(group_id: int) -> dict:
    with _lock:
        return dict(_jobs.get(group_id, {"status": "idle", "progress": 0, "error": None}))


def _is_running(group_id: int) -> bool:
    with _lock:
        if _jobs.get(group_id, {}).get("status") != "running":
            return False
    # Verify the worker thread is actually still alive; if the thread died
    # without clearing the status (e.g. process killed), reset to error so
    # the user can try again instead of getting a permanent 409.
    thread_name_a = f"archive-{group_id}"
    thread_name_r = f"restore-{group_id}"
    alive = any(t.name in (thread_name_a, thread_name_r) for t in threading.enumerate())
    if not alive:
        _set_job(
            group_id,
            {"status": "error", "progress": 0, "error": "Worker thread died unexpectedly."},
        )
        return False
    return True


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _safe_name(name: str) -> str:
    """Strip characters that are invalid in file names."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip() or "group"


# â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def start_archive(group_id: int, archive_dir: str) -> None:
    """Kick off background compression for *group_id*."""
    _set_job(group_id, {"status": "running", "progress": 0, "error": None})
    t = threading.Thread(
        target=_archive_worker,
        args=(group_id, archive_dir),
        daemon=True,
        name=f"archive-{group_id}",
    )
    t.start()


def start_restore(group_id: int) -> None:
    """Kick off background restore for *group_id*."""
    _set_job(group_id, {"status": "running", "progress": 0, "error": None})
    t = threading.Thread(
        target=_restore_worker,
        args=(group_id,),
        daemon=True,
        name=f"restore-{group_id}",
    )
    t.start()


# â”€â”€ Workers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _archive_worker(group_id: int, archive_dir: str) -> None:
    db = SessionLocal()
    job_row: ArchiveJob | None = None
    try:
        # Signal immediately so the UI shows progress > 0 right away
        _set_job(group_id, {"status": "running", "progress": 1, "error": None})

        grp = db.get(FileGroup, group_id)
        if not grp:
            _set_job(group_id, {"status": "error", "progress": 0, "error": "Group not found."})
            return

        # Persist job record
        job_row = ArchiveJob(
            group_id=group_id,
            group_name=grp.name,
            action="archive",
            status="running",
        )
        db.add(job_row)
        db.commit()
        db.refresh(job_row)

        root = Path(grp.root_path)
        if not root.exists():
            err = f"Root path not found: {root}"
            _set_job(group_id, {"status": "error", "progress": 0, "error": err})
            job_row.status = "error"
            job_row.error_msg = err
            job_row.finished_at = datetime.datetime.utcnow()
            db.commit()
            return

        dest_dir = Path(archive_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        safe = _safe_name(grp.name)
        zip_path = dest_dir / f"{safe}_{group_id}.zip"

        # â”€â”€ Step 1: copy SHARED DLLs to shared storage, get back a manifest list â”€â”€
        _set_job(group_id, {"status": "running", "progress": 2, "error": None})
        shared_dir = settings_service.load_settings().get("dedup_shared_dir", "").strip()
        dll_manifest: list[dict] = []
        shared_paths_saved: set[Path] = set()
        if shared_dir:
            try:

                def _dll_scan_progress(pct: int) -> None:
                    # Map 0-100 from scan phase â†’ 2-9% overall
                    overall = 2 + int(pct * 7 / 100)
                    _set_job(group_id, {"status": "running", "progress": overall, "error": None})

                dll_manifest = dedup_service.extract_dlls_inline(
                    group_id,
                    grp.name,
                    root,
                    shared_dir,
                    db,
                    progress_callback=_dll_scan_progress,
                )
                # Only exclude the specific files that were actually saved to shared storage
                shared_paths_saved = {Path(e["original_path"]) for e in dll_manifest}
            except Exception as dll_exc:
                logger.warning(
                    "DLL extraction during archive for group %d failed: %s", group_id, dll_exc
                )

        # â”€â”€ Step 2: zip game files (unique DLLs included, shared DLLs excluded) + embed manifest â”€â”€
        _set_job(group_id, {"status": "running", "progress": 10, "error": None})
        all_files = [p for p in root.rglob("*") if p.is_file() and p not in shared_paths_saved]
        total = len(all_files)
        logger.info("Archiving group %d (%s): %d files â†’ %s", group_id, grp.name, total, zip_path)

        dll_manifest_json = json.dumps(
            {"group_id": group_id, "group_name": grp.name, "dlls": dll_manifest},
            indent=2,
        ).encode("utf-8")

        with zipfile.ZipFile(
            zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as zf:
            for i, fp in enumerate(all_files):
                arcname = fp.relative_to(root.parent)
                zf.write(fp, arcname)
                # Scale 10% â†’ 90% across the file list
                pct = 10 + int((i + 1) / max(total, 1) * 80)
                _set_job(group_id, {"status": "running", "progress": pct, "error": None})
            # Always embed the manifest (empty list if no shared dir configured)
            zf.writestr("_dlls.json", dll_manifest_json)
        _set_job(group_id, {"status": "running", "progress": 90, "error": None})

        logger.info("DLL manifest embedded in zip (%d DLLs)", len(dll_manifest))

        # â”€â”€ Step 3: delete original tree â”€â”€
        shutil.rmtree(root)

        # Persist to DB
        archive_size = zip_path.stat().st_size
        grp.is_archived = True
        grp.archive_path = str(zip_path)
        grp.archived_at = datetime.datetime.utcnow()
        grp.archive_size_bytes = float(archive_size)

        db.query(FileRecord).filter(FileRecord.group_id == group_id).update({"is_missing": True})

        job_row.status = "done"
        job_row.archive_path = str(zip_path)
        job_row.archive_size_bytes = float(archive_size)
        job_row.finished_at = datetime.datetime.utcnow()
        db.commit()

        _set_job(group_id, {"status": "done", "progress": 100, "error": None})
        logger.info(
            "Archive done for group %d â†’ %s (%.1f MB)", group_id, zip_path, archive_size / 1e6
        )

        # â”€â”€ Step 5: remove shared DLL zips no longer needed by any active game â”€â”€
        if shared_dir:
            try:
                dedup_service.cleanup_orphaned_shared_dlls(group_id, shared_dir, db)
            except Exception as cleanup_exc:
                logger.warning("Shared DLL cleanup failed for group %d: %s", group_id, cleanup_exc)

    except Exception as exc:
        logger.exception("Archive failed for group %d", group_id)
        db.rollback()
        _set_job(group_id, {"status": "error", "progress": 0, "error": str(exc)})
        if job_row and job_row.id:
            try:
                job_row.status = "error"
                job_row.error_msg = str(exc)
                job_row.finished_at = datetime.datetime.utcnow()
                db.commit()
            except Exception:
                pass
    finally:
        db.close()


def _restore_worker(group_id: int) -> None:
    db = SessionLocal()
    job_row: ArchiveJob | None = None
    try:
        grp = db.get(FileGroup, group_id)
        if not grp:
            _set_job(group_id, {"status": "error", "progress": 0, "error": "Group not found."})
            return

        if not grp.is_archived or not grp.archive_path:
            _set_job(
                group_id, {"status": "error", "progress": 0, "error": "Group is not archived."}
            )
            return

        # Persist job record
        job_row = ArchiveJob(
            group_id=group_id,
            group_name=grp.name,
            action="restore",
            status="running",
        )
        db.add(job_row)
        db.commit()
        db.refresh(job_row)

        zip_path = Path(grp.archive_path)
        if not zip_path.exists():
            err = f"Archive file not found: {zip_path}"
            _set_job(group_id, {"status": "error", "progress": 0, "error": err})
            job_row.status = "error"
            job_row.error_msg = err
            job_row.finished_at = datetime.datetime.utcnow()
            db.commit()
            return

        extract_to = Path(grp.root_path).parent
        extract_to.mkdir(parents=True, exist_ok=True)

        logger.info("Restoring group %d (%s) from %s", group_id, grp.name, zip_path)

        # â”€â”€ Step 1: read embedded _dlls.json, then extract game files â”€â”€
        dll_entries: list[dict] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "_dlls.json" in zf.namelist():
                dll_entries = json.loads(zf.read("_dlls.json").decode("utf-8")).get("dlls", [])
            members = [m for m in zf.namelist() if m != "_dlls.json"]
            total = len(members)
            for i, member in enumerate(members):
                zf.extract(member, extract_to)
                pct = int((i + 1) / max(total, 1) * 70)
                _set_job(group_id, {"status": "running", "progress": pct, "error": None})

        # â”€â”€ Step 2: restore DLLs from shared storage â”€â”€
        # Legacy fallback: manifests written before embedded-json was introduced
        if not dll_entries:
            shared_dir = settings_service.load_settings().get("dedup_shared_dir", "").strip()
            legacy = Path(shared_dir) / "manifests" / f"{group_id}.json" if shared_dir else Path()
            if legacy.exists():
                dll_entries = json.loads(legacy.read_text(encoding="utf-8")).get("dlls", [])

        if dll_entries:
            try:
                total_dlls = len(dll_entries)
                restored = 0
                for j, entry in enumerate(dll_entries):
                    dll_zip = Path(entry.get("archive_path", ""))
                    dest = Path(entry.get("original_path", ""))
                    if not dll_zip.exists():
                        logger.warning("DLL zip missing, skipping: %s", dll_zip)
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with zipfile.ZipFile(str(dll_zip), "r") as zf:
                            stored_name = zf.namelist()[0]
                            zf.extract(stored_name, str(dest.parent))
                        extracted_file = dest.parent / Path(stored_name).name
                        if extracted_file != dest and extracted_file.exists():
                            extracted_file.rename(dest)
                        restored += 1
                    except Exception as dll_exc:
                        logger.warning("DLL restore failed for %s: %s", dest, dll_exc)
                    pct = 70 + int((j + 1) / max(total_dlls, 1) * 25)
                    _set_job(group_id, {"status": "running", "progress": pct, "error": None})
                logger.info(
                    "DLL restore for group %d: %d/%d DLLs restored", group_id, restored, total_dlls
                )
            except Exception as manifest_exc:
                logger.warning(
                    "DLL manifest restore failed for group %d: %s", group_id, manifest_exc
                )

        # â”€â”€ Step 3: clean up archive zip â”€â”€
        zip_path.unlink()

        # Update DB
        grp.is_archived = False
        grp.archive_path = None
        grp.archived_at = None
        grp.archive_size_bytes = None

        db.query(FileRecord).filter(FileRecord.group_id == group_id).update({"is_missing": False})

        job_row.status = "done"
        job_row.finished_at = datetime.datetime.utcnow()
        db.commit()

        _set_job(group_id, {"status": "done", "progress": 100, "error": None})
        logger.info("Restore done for group %d", group_id)

    except Exception as exc:
        logger.exception("Restore failed for group %d", group_id)
        db.rollback()
        _set_job(group_id, {"status": "error", "progress": 0, "error": str(exc)})
        if job_row and job_row.id:
            try:
                job_row.status = "error"
                job_row.error_msg = str(exc)
                job_row.finished_at = datetime.datetime.utcnow()
                db.commit()
            except Exception:
                pass
    finally:
        db.close()
