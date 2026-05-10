"""
Archive API — settings + per-group archive / restore endpoints.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.services import archive_service, settings_service
from database.models import ArchiveJob, FileGroup, get_db

router = APIRouter(prefix="/api/archive", tags=["Archive"])


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings")
def get_settings():
    """Return current application settings."""
    return settings_service.load_settings()


class SettingsUpdate(BaseModel):
    archive_dir: str
    dedup_shared_dir: str = ""


@router.put("/settings")
def update_settings(body: SettingsUpdate):
    """Persist updated settings and return the full settings object."""
    archive_dir = body.archive_dir.strip()
    dedup_shared_dir = body.dedup_shared_dir.strip()
    # Basic sanity check: path must not contain obvious traversal sequences
    if ".." in Path(archive_dir).parts:
        raise HTTPException(400, "Invalid archive directory path.")
    if dedup_shared_dir and ".." in Path(dedup_shared_dir).parts:
        raise HTTPException(400, "Invalid shared DLL directory path.")
    return settings_service.save_settings({"archive_dir": archive_dir, "dedup_shared_dir": dedup_shared_dir})


# ── Archive / Restore ─────────────────────────────────────────────────────────

@router.post("/{group_id}/archive")
def archive_group(group_id: int, db: Session = Depends(get_db)):
    """Compress group files into a zip and delete originals."""
    grp = db.get(FileGroup, group_id)
    if not grp:
        raise HTTPException(404, "Group not found.")
    if grp.is_archived:
        raise HTTPException(400, "Group is already archived.")

    settings = settings_service.load_settings()
    archive_dir = settings.get("archive_dir", "").strip()
    if not archive_dir:
        raise HTTPException(
            400, "Archive directory is not configured. Set it in Settings (⚙)."
        )

    if archive_service._is_running(group_id):  # noqa: SLF001
        raise HTTPException(409, "An archive/restore job is already running for this group.")

    archive_service.start_archive(group_id, archive_dir)
    return {"message": "Archive started.", "group_id": group_id}


@router.post("/{group_id}/restore")
def restore_group(group_id: int, db: Session = Depends(get_db)):
    """Extract the zip back to the original root path."""
    grp = db.get(FileGroup, group_id)
    if not grp:
        raise HTTPException(404, "Group not found.")
    if not grp.is_archived:
        raise HTTPException(400, "Group is not archived.")

    if archive_service._is_running(group_id):  # noqa: SLF001
        raise HTTPException(409, "An archive/restore job is already running for this group.")

    archive_service.start_restore(group_id)
    return {"message": "Restore started.", "group_id": group_id}


@router.get("/{group_id}/status")
def archive_status(group_id: int):
    """Poll the progress of an ongoing archive or restore job."""
    return archive_service.get_status(group_id)


@router.get("/history")
def archive_history(limit: int = 200, db: Session = Depends(get_db)):
    """Return recent archive / restore job history, newest first."""
    jobs = (
        db.query(ArchiveJob)
        .order_by(ArchiveJob.started_at.desc())
        .limit(limit)
        .all()
    )
    return [j.to_dict() for j in jobs]
