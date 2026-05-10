"""
Files API endpoints — search, filter, update, stats.
Heavy operations (recategorize, regroup) are proxied to worker-service via main.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from diskassistent_db.models import FileRecord, get_db

router = APIRouter(prefix="/api/files", tags=["Files"])

CATEGORIES = [
    "Games",
    "Movies",
    "Music",
    "Images",
    "Documents",
    "Software",
    "Archives",
    "Other",
]


# ── Read ──────────────────────────────────────────────────────────────────────


@router.get("/")
def list_files(
    category: str | None = None,
    extension: str | None = None,
    search: str | None = None,
    missing: bool | None = None,
    group_id: int | None = None,
    limit: int = Query(100, le=500),
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
        q = q.filter(FileRecord.name.like(pattern) | FileRecord.full_path.like(pattern))
    if missing is not None:
        q = q.filter(FileRecord.is_missing == missing)
    if group_id is not None:
        if group_id == 0:
            q = q.filter(FileRecord.group_id == None)  # noqa: E711
        else:
            q = q.filter(FileRecord.group_id == group_id)

    total = q.count()
    items = q.order_by(FileRecord.name).offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "limit": limit, "items": [f.to_dict() for f in items]}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Return aggregate statistics about indexed files."""
    from sqlalchemy import func

    total_files = db.query(func.count(FileRecord.id)).scalar()
    total_size = db.query(func.sum(FileRecord.size_bytes)).scalar() or 0

    by_category = (
        db.query(FileRecord.category, func.count(FileRecord.id)).group_by(FileRecord.category).all()
    )
    by_ext = (
        db.query(FileRecord.extension, func.count(FileRecord.id))
        .group_by(FileRecord.extension)
        .order_by(func.count(FileRecord.id).desc())
        .limit(20)
        .all()
    )
    missing_count = (
        db.query(func.count(FileRecord.id))
        .filter(FileRecord.is_missing == True)  # noqa: E712
        .scalar()
    )

    return {
        "total_files": total_files,
        "total_size": total_size,
        "missing_files": missing_count,
        "by_category": [{"category": c, "count": n} for c, n in by_category],
        "by_extension": [{"extension": e or "(none)", "count": n} for e, n in by_ext],
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


# ── Update ────────────────────────────────────────────────────────────────────


class FileUpdate(BaseModel):
    category: str | None = None
    tags: str | None = None
    description: str | None = None


@router.patch("/{file_id}")
def update_file(file_id: int, body: FileUpdate, db: Session = Depends(get_db)):
    rec = db.get(FileRecord, file_id)
    if not rec:
        raise HTTPException(404, "File not found.")
    if body.category is not None:
        rec.category = body.category
        rec.category_overridden = True
    if body.tags is not None:
        rec.tags = body.tags
    if body.description is not None:
        rec.description = body.description
    db.commit()
    db.refresh(rec)
    return rec.to_dict()


# ── Cleanup ───────────────────────────────────────────────────────────────────


@router.post("/cleanup")
def cleanup_missing(db: Session = Depends(get_db)):
    """Remove DB records for files that no longer exist on disk."""
    import os

    records = db.query(FileRecord).all()
    removed = 0
    for rec in records:
        if not os.path.exists(rec.full_path):
            rec.is_missing = True
            removed += 1
    db.commit()
    return {"marked_missing": removed}
