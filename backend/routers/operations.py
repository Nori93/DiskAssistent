"""
File operations API endpoints — move, rename, delete.
"""

from __future__ import annotations

import os
import subprocess
import sys

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.services.file_ops import (
    FileOperationError,
    delete_file,
    move_file,
    rename_file,
)
from database.models import FileRecord, get_db

router = APIRouter(prefix="/api/operations", tags=["Operations"])


class MoveBody(BaseModel):
    file_id: int
    dest_dir: str


class RenameBody(BaseModel):
    file_id: int
    new_name: str


class DeleteBody(BaseModel):
    file_id: int
    confirm: bool = False  # client must explicitly send confirm=true


class OpenFolderBody(BaseModel):
    path: str


@router.post("/open-folder")
def open_folder(body: OpenFolderBody):
    """Open a folder in the native file manager (Windows Explorer, Nautilus, Finder).
    If the path is a file, open its parent directory.
    """
    path = body.path.strip().rstrip("\\/")  # strip trailing separators

    # If it looks like a file, open the parent directory
    if os.path.isfile(path):
        path = os.path.dirname(path)

    try:
        if sys.platform == "win32":
            # os.startfile uses ShellExecuteW — single-instance, no double windows
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        raise HTTPException(500, f"Could not open folder: {exc}") from exc

    return {"opened": path}


@router.post("/move")
def move(body: MoveBody, db: Session = Depends(get_db)):
    rec = _get_or_404(db, body.file_id)
    try:
        new_path = move_file(rec.full_path, body.dest_dir)
    except FileOperationError as exc:
        raise HTTPException(400, str(exc)) from exc

    # Update DB record
    from pathlib import Path

    new_p = Path(new_path)
    rec.full_path = new_path
    rec.parent_dir = str(new_p.parent)
    rec.name = new_p.name
    db.commit()
    db.refresh(rec)
    return {"message": "File moved.", "file": rec.to_dict()}


@router.post("/rename")
def rename(body: RenameBody, db: Session = Depends(get_db)):
    rec = _get_or_404(db, body.file_id)
    try:
        new_path = rename_file(rec.full_path, body.new_name)
    except FileOperationError as exc:
        raise HTTPException(400, str(exc)) from exc

    from pathlib import Path

    new_p = Path(new_path)
    rec.full_path = new_path
    rec.name = new_p.name
    rec.extension = new_p.suffix.lower()
    db.commit()
    db.refresh(rec)
    return {"message": "File renamed.", "file": rec.to_dict()}


@router.delete("/delete")
def delete(body: DeleteBody, db: Session = Depends(get_db)):
    if not body.confirm:
        raise HTTPException(400, "You must set confirm=true to delete a file.")
    rec = _get_or_404(db, body.file_id)
    try:
        delete_file(rec.full_path)
    except FileOperationError as exc:
        raise HTTPException(400, str(exc)) from exc

    db.delete(rec)
    db.commit()
    return {"message": "File deleted."}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_or_404(db: Session, file_id: int) -> FileRecord:
    rec = db.get(FileRecord, file_id)
    if not rec:
        raise HTTPException(404, "File not found.")
    return rec
