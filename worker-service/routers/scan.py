"""
Scanning API endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from diskassistent_db.models import ScanJob, SessionLocal
from services.scan_service import get_active_scan, get_job_status, start_rescan_all, start_scan

router = APIRouter(prefix="/api/scan", tags=["Scanning"])


class ScanRequest(BaseModel):
    path: str


@router.post("/start")
def start_scan_endpoint(body: ScanRequest):
    if not body.path.strip():
        raise HTTPException(400, "Path must not be empty.")
    job_id = start_scan(body.path.strip())
    return {"job_id": job_id, "message": "Scan started."}


@router.post("/rescan-all")
def rescan_all_endpoint():
    try:
        job_id = start_rescan_all()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"job_id": job_id, "message": "Rescan of all disks started."}


@router.get("/active")
def active_scan():
    job = get_active_scan()
    return job if job else {"job_id": None}


@router.get("/status/{job_id}")
def scan_status(job_id: int):
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(404, f"No scan job with id={job_id}")
    return status


@router.get("/history")
def scan_history():
    db = SessionLocal()
    try:
        jobs = db.query(ScanJob).order_by(ScanJob.id.desc()).limit(50).all()
        return [j.to_dict() for j in jobs]
    finally:
        db.close()
