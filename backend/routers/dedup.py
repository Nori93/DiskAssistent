"""
DLL Deduplication API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.services import dedup_service, settings_service
from database.models import get_db

router = APIRouter(prefix="/api/dedup", tags=["Dedup"])


# ── Request bodies ────────────────────────────────────────────────────────────


class AnalyzeBody(BaseModel):
    group_ids: list[int] | None = None  # None = all groups


class ApplyBody(BaseModel):
    group_ids: list[int] | None = None
    shared_dir: str | None = None  # override settings if provided


class RestoreBody(BaseModel):
    group_ids: list[int] | None = None


class ExtractAllBody(BaseModel):
    group_ids: list[int] | None = None
    shared_dir: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/analyze")
def analyze(body: AnalyzeBody):
    """Scan game groups and find duplicate DLLs (read-only, no changes made)."""
    job_id = dedup_service.start_analyze(body.group_ids)
    return {"job_id": job_id, "message": "Analysis started."}


@router.post("/apply")
def apply(body: ApplyBody):
    """Replace duplicate DLLs with hard/symlinks pointing to shared storage."""
    shared_dir = (body.shared_dir or "").strip()
    if not shared_dir:
        settings = settings_service.load_settings()
        shared_dir = settings.get("dedup_shared_dir", "").strip()
    if not shared_dir:
        raise HTTPException(
            400,
            "Shared DLL directory is not configured. Set it in Settings (⚙) → Dedup.",
        )
    job_id = dedup_service.start_apply(shared_dir, body.group_ids)
    return {"job_id": job_id, "message": "Deduplication started."}


@router.post("/restore")
def restore(body: RestoreBody):
    """Restore all tracked links back to real file copies."""
    job_id = dedup_service.start_restore(body.group_ids)
    return {"job_id": job_id, "message": "Restore started."}


@router.post("/extract")
def extract_all(body: ExtractAllBody):
    """Extract ALL DLLs from game groups into shared storage with zip backups and index.json."""
    shared_dir = (body.shared_dir or "").strip()
    if not shared_dir:
        settings = settings_service.load_settings()
        shared_dir = settings.get("dedup_shared_dir", "").strip()
    if not shared_dir:
        raise HTTPException(
            400,
            "Shared DLL directory is not configured. Set it in Settings (⚙) → Dedup.",
        )
    job_id = dedup_service.start_extract_all(shared_dir, body.group_ids)
    return {"job_id": job_id, "message": "DLL extraction started."}


@router.get("/job/{job_id}")
def job_status(job_id: str):
    """Poll progress of an analyze / apply / restore job."""
    job = dedup_service.get_job(job_id)
    if job.get("status") == "not_found":
        raise HTTPException(404, "Job not found.")
    return job


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Return current deduplication statistics (from DB)."""
    return dedup_service.get_db_stats(db)
