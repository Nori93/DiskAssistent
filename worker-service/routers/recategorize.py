"""
Recategorize & Regroup API endpoints (extracted from the monolith files router).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import recategorize_service

router = APIRouter(prefix="/api/files", tags=["Recategorize"])


class RecategorizeRequest(BaseModel):
    only_auto: bool = True
    category: str | None = None
    group_id: int | None = None
    regroup: bool = True


@router.post("/recategorize")
def recategorize_files(body: RecategorizeRequest):
    parts = []
    if body.category:
        parts.append(f"category:{body.category}")
    if body.group_id is not None:
        parts.append(f"group:{body.group_id}")
    if body.only_auto:
        parts.append("auto-only")
    scope = ",".join(parts) if parts else "all"

    job_id = recategorize_service.start_recategorize(
        scope, body.only_auto, body.category, body.group_id, body.regroup
    )
    return {"job_id": job_id, "message": "Re-categorize started."}


@router.get("/recategorize/status/{job_id}")
def recategorize_status(job_id: int):
    status = recategorize_service.get_recategorize_status(job_id)
    if not status:
        raise HTTPException(404, f"No recategorize job with id={job_id}")
    return status


@router.get("/recategorize/history")
def recategorize_history():
    return recategorize_service.get_recategorize_history()


@router.post("/regroup")
def regroup():
    """Rebuild all groups from current DB records."""
    from diskassistent_db.models import SessionLocal
    from services.grouper import build_groups

    db = SessionLocal()
    try:
        count = build_groups(db)
        return {"message": f"Regrouped. {count} groups created/updated."}
    finally:
        db.close()
