"""
Scanning API endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.scan_service import (
    get_active_scan,
    get_job_status,
    start_rescan_all,
    start_scan,
)
from database.models import ScanJob, SessionLocal

router = APIRouter(prefix="/api/scan", tags=["Scanning"])


class ScanRequest(BaseModel):
    path: str


@router.post("/start")
def start_scan_endpoint(body: ScanRequest):
    """Start a background scan job for *path*."""
    if not body.path.strip():
        raise HTTPException(400, "Path must not be empty.")
    job_id = start_scan(body.path.strip())
    return {"job_id": job_id, "message": "Scan started."}


@router.post("/rescan-all")
def rescan_all_endpoint():
    """
    Wipe the database and rescan every disk/mount point from scratch.
    Returns a job_id that can be polled via GET /api/scan/status/{job_id}.
    """
    try:
        job_id = start_rescan_all()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"job_id": job_id, "message": "Rescan of all disks started."}


@router.get("/active")
def active_scan():
    """
    Return the currently running/pending scan job, or null.
    The frontend calls this on every page load to reconnect to an in-progress scan.
    """
    job = get_active_scan()
    return job if job else {"job_id": None}


@router.get("/status/{job_id}")
def scan_status(job_id: int):
    """Get the status and progress of a scan job."""
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(404, f"No scan job with id={job_id}")
    return status


@router.get("/history")
def scan_history():
    """Return the 50 most recent scan jobs, newest first."""
    db = SessionLocal()
    try:
        jobs = db.query(ScanJob).order_by(ScanJob.id.desc()).limit(50).all()
        return [j.to_dict() for j in jobs]
    finally:
        db.close()
