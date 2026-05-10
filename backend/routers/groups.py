"""
File groups API endpoints.
"""

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, defer

from database.models import FileGroup, FileRecord, get_db

router = APIRouter(prefix="/api/groups", tags=["Groups"])


@router.get("/")
def list_groups(category: str | None = None, db: Session = Depends(get_db)):
    """Return all groups, optionally filtered by category."""
    # Defer file_tree_json — it can be several MB per group and is not needed for listing.
    q = (
        db.query(FileGroup)
        .options(defer(FileGroup.file_tree_json))
        .order_by(FileGroup.name)
    )
    if category:
        q = q.filter(FileGroup.category == category)
    groups = q.all()

    # Single aggregated count query instead of N correlated subqueries.
    counts: dict[int, int] = {}
    if groups:
        group_ids = [g.id for g in groups]
        count_rows = (
            db.query(FileRecord.group_id, func.count(FileRecord.id))
            .filter(FileRecord.group_id.in_(group_ids))
            .group_by(FileRecord.group_id)
            .all()
        )
        counts = dict(count_rows)

    result = []
    for grp in groups:
        d = grp.to_dict()
        d["file_count"] = counts.get(grp.id, 0)
        result.append(d)

    # Count ungrouped files
    ungrouped_q = db.query(func.count(FileRecord.id)).filter(
        FileRecord.group_id == None  # noqa: E711
    )
    if category:
        ungrouped_q = ungrouped_q.filter(FileRecord.category == category)

    return {"groups": result, "ungrouped_count": ungrouped_q.scalar() or 0}


@router.get("/{group_id}")
def get_group(group_id: int, db: Session = Depends(get_db)):
    grp = db.get(FileGroup, group_id)
    if not grp:
        raise HTTPException(404, "Group not found.")
    d = grp.to_dict()
    d["files"] = [
        f.to_dict() for f in db.query(FileRecord).filter(FileRecord.group_id == group_id).all()
    ]
    return d


@router.get("/{group_id}/tree")
def get_group_tree(group_id: int, db: Session = Depends(get_db)):
    """Return the full directory tree for a group.
    The tree is built once and cached in file_tree_json; invalidated on rescan/regroup.
    """
    grp = db.get(FileGroup, group_id)
    if not grp:
        raise HTTPException(404, "Group not found.")

    if grp.file_tree_json:
        return json.loads(grp.file_tree_json)

    tree = _build_group_tree(db, grp)
    grp.file_tree_json = json.dumps(tree, separators=(",", ":"))
    db.commit()
    return tree


def _build_group_tree(db, grp: FileGroup) -> dict:
    """Build a nested directory tree from a group's file records."""
    sep = os.sep
    root_path = grp.root_path.rstrip(sep)
    root_lower = root_path.lower()

    files = (
        db.query(FileRecord)
        .filter(FileRecord.group_id == grp.id)
        .order_by(FileRecord.full_path)
        .all()
    )

    root_node: dict = {
        "name": os.path.basename(root_path) or root_path,
        "path": root_path,
        "children": {},
        "files": [],
    }

    for f in files:
        rel = f.full_path
        rel = rel[len(root_path) :].lstrip("/\\") if rel.lower().startswith(root_lower) else f.name

        # Split into folder parts (drop the filename at the end)
        parts = rel.replace("\\", "/").split("/")
        parts.pop()  # last element is the filename, not a folder

        node = root_node
        for part in parts:
            if not part:
                continue
            if part not in node["children"]:
                node["children"][part] = {
                    "name": part,
                    "path": node["path"] + sep + part,
                    "children": {},
                    "files": [],
                }
            node = node["children"][part]

        node["files"].append(f.to_dict())

    return root_node


class UpdateGroupBody(BaseModel):
    category: str | None = None
    description: str | None = None


@router.patch("/{group_id}")
def update_group(group_id: int, body: UpdateGroupBody, db: Session = Depends(get_db)):
    grp = db.get(FileGroup, group_id)
    if not grp:
        raise HTTPException(404, "Group not found.")
    if body.category is not None:
        grp.category = body.category
    if body.description is not None:
        grp.description = body.description
    db.commit()
    db.refresh(grp)
    return grp.to_dict()


@router.post("/{group_id}/refresh-icon")
def refresh_group_icon(group_id: int, db: Session = Depends(get_db)):
    """Re-extract the exe icon for a group and store it in thumbnail_path."""
    from backend.services.icon_service import extract_group_icon, pick_best_exe

    grp = db.get(FileGroup, group_id)
    if not grp:
        raise HTTPException(404, "Group not found.")

    exe = pick_best_exe(db, group_id, grp.root_path)
    if not exe:
        return {"thumbnail_path": grp.thumbnail_path, "skipped": True, "reason": "no_exe"}

    url = extract_group_icon(group_id, exe)
    if not url:
        return {"thumbnail_path": grp.thumbnail_path, "skipped": True, "reason": "extraction_failed"}

    grp.thumbnail_path = url
    db.commit()
    return {"thumbnail_path": url, "skipped": False}


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    """Remove the group record (and unlink its files). Files on disk are NOT deleted."""
    grp = db.get(FileGroup, group_id)
    if not grp:
        raise HTTPException(404, "Group not found.")
    # Unlink all member files so they appear as ungrouped on the next scan
    db.query(FileRecord).filter(FileRecord.group_id == group_id).update({"group_id": None})
    db.delete(grp)
    db.commit()
    return {"message": f"Group '{grp.name}' deleted."}
