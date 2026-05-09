"""
Files API endpoints — search, filter, update, stats.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.models import FileRecord, get_db
from ai.categorizer import CATEGORIES

router = APIRouter(prefix="/api/files", tags=["Files"])


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/")
def list_files(
    category: Optional[str] = None,
    extension: Optional[str] = None,
    search:    Optional[str] = None,
    missing:   Optional[bool]= None,
    group_id:  Optional[int] = None,
    limit:  int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Return paginated list of files with optional filters."""
    q = db.query(FileRecord)
    if category:
        q = q.filter(FileRecord.category == category)
    if extension:
        ext = extension if extension.startswith(".") else f".{extension}"
        q = q.filter(FileRecord.extension == ext.lower())
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            FileRecord.name.like(pattern) | FileRecord.full_path.like(pattern)
        )
    if missing is not None:
        q = q.filter(FileRecord.is_missing == missing)
    if group_id is not None:
        if group_id == 0:
            # Special sentinel: files with NO group assigned
            q = q.filter(FileRecord.group_id == None)  # noqa: E711
        else:
            q = q.filter(FileRecord.group_id == group_id)

    total = q.count()
    items = q.order_by(FileRecord.name).offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "limit": limit,
            "items": [f.to_dict() for f in items]}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Return aggregate statistics about indexed files."""
    from sqlalchemy import func
    total_files = db.query(func.count(FileRecord.id)).scalar()
    total_size  = db.query(func.sum(FileRecord.size_bytes)).scalar() or 0

    by_category = (
        db.query(FileRecord.category, func.count(FileRecord.id))
        .group_by(FileRecord.category)
        .all()
    )
    by_ext = (
        db.query(FileRecord.extension, func.count(FileRecord.id))
        .group_by(FileRecord.extension)
        .order_by(func.count(FileRecord.id).desc())
        .limit(20)
        .all()
    )
    missing_count = db.query(func.count(FileRecord.id)).filter(
        FileRecord.is_missing == True  # noqa: E712
    ).scalar()

    return {
        "total_files":   total_files,
        "total_size":    total_size,
        "missing_files": missing_count,
        "by_category":   [{"category": c, "count": n} for c, n in by_category],
        "by_extension":  [{"extension": e or "(none)", "count": n} for e, n in by_ext],
    }


@router.get("/categories")
def list_categories():
    return CATEGORIES


@router.get("/{file_id}")
def get_file(file_id: int, db: Session = Depends(get_db)):
    rec = db.get(FileRecord, file_id)
    if not rec:
        raise HTTPException(404, "File not found.")
    return rec.to_dict()


# ── Re-categorize ─────────────────────────────────────────────────────────────

class RecategorizeRequest(BaseModel):
    only_auto: bool = True      # True = skip files the user overrode manually
    category:  Optional[str] = None   # limit to files currently in this category
    group_id:  Optional[int] = None   # limit to files in this group
    regroup:   bool = True            # also rebuild groups from DB after recategorizing


@router.post("/recategorize")
def recategorize_files(body: RecategorizeRequest):
    """
    Start a background recategorize + regroup job and return its job_id immediately.
    Poll GET /api/files/recategorize/status/{job_id} for progress.
    """
    from backend.services.recategorize_service import start_recategorize

    parts = []
    if body.category:
        parts.append(f"category:{body.category}")
    if body.group_id is not None:
        parts.append(f"group:{body.group_id}")
    if body.only_auto:
        parts.append("auto-only")
    scope = ",".join(parts) if parts else "all"

    job_id = start_recategorize(scope, body.only_auto, body.category, body.group_id, body.regroup)
    return {"job_id": job_id, "message": "Re-categorize started."}


@router.get("/recategorize/status/{job_id}")
def recategorize_status(job_id: int):
    """Poll the status and progress of a recategorize job."""
    from backend.services.recategorize_service import get_recategorize_status
    status = get_recategorize_status(job_id)
    if not status:
        raise HTTPException(404, f"No recategorize job with id={job_id}")
    return status


@router.get("/recategorize/history")
def recategorize_history():
    """Return the 50 most recent recategorize jobs, newest first."""
    from backend.services.recategorize_service import get_recategorize_history
    return get_recategorize_history()


@router.post("/regroup")
def regroup_files():
    """
    Rebuild all file groups from the current database without touching the
    disk or recategorizing anything.  Returns immediately; poll
    GET /api/files/recategorize/status/{job_id} for progress
    (a RecategorizeJob is created with scope='regroup-only').
    """
    from backend.services.recategorize_service import start_recategorize
    job_id = start_recategorize("regroup-only", only_auto=False, category=None, group_id=None, regroup=True, skip_categorize=True)
    return {"job_id": job_id, "message": "Regroup started."}


# ── Cleanup ───────────────────────────────────────────────────────────────────

@router.post("/cleanup")
def cleanup_database(db: Session = Depends(get_db)):
    """
    Clean the database:
      1. Delete records for files that no longer exist on disk.
      2. Re-run categorization on every non-overridden file whose stored
         category no longer matches the current rules.
    Returns counts of removed and fixed records.
    """
    import os
    from ai.categorizer import categorize
    from backend.config import logger

    all_records = db.query(FileRecord).all()
    removed = 0
    fixed   = 0

    for rec in all_records:
        # 1. Remove orphaned records (file deleted from disk)
        if not os.path.exists(rec.full_path):
            db.delete(rec)
            removed += 1
            continue

        # 2. Fix wrong auto-categories
        if not rec.category_overridden:
            new_cat = categorize(rec.full_path)
            if new_cat != rec.category:
                rec.ai_category = new_cat
                rec.category    = new_cat
                fixed += 1

    db.commit()
    logger.info("Cleanup: removed=%d fixed=%d", removed, fixed)
    return {
        "removed": removed,
        "fixed":   fixed,
        "message": f"Removed {removed} missing files, fixed {fixed} wrong categories.",
    }


# ── Update ────────────────────────────────────────────────────────────────────

class UpdateFileBody(BaseModel):
    category:    Optional[str] = None
    tags:        Optional[str] = None
    description: Optional[str] = None


@router.patch("/{file_id}")
def update_file(file_id: int, body: UpdateFileBody, db: Session = Depends(get_db)):
    """Update category, tags, or description for a file."""
    rec = db.get(FileRecord, file_id)
    if not rec:
        raise HTTPException(404, "File not found.")

    if body.category is not None:
        if body.category not in CATEGORIES:
            raise HTTPException(400, f"Invalid category. Choose from: {CATEGORIES}")
        rec.category             = body.category
        rec.category_overridden  = True
    if body.tags is not None:
        rec.tags = body.tags
    if body.description is not None:
        rec.description = body.description

    db.commit()
    db.refresh(rec)
    return rec.to_dict()
