"""
File operations API endpoints — move, rename, delete.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import HOST_AGENT_SECRET, HOST_AGENT_URL
from diskassistent_db.models import FileRecord, get_db
from services.file_ops import FileOperationError, delete_file, move_file, rename_file

router = APIRouter(prefix="/api/operations", tags=["Operations"])


# ── Agent helper ──────────────────────────────────────────────────────────────


def _agent_post(endpoint: str, data: dict) -> dict:
    import httpx

    headers = {"Authorization": f"Bearer {HOST_AGENT_SECRET}"} if HOST_AGENT_SECRET else {}
    resp = httpx.post(f"{HOST_AGENT_URL}{endpoint}", json=data, headers=headers, timeout=60.0)
    resp.raise_for_status()
    return resp.json()


# ── Request models ────────────────────────────────────────────────────────────


class MoveBody(BaseModel):
    file_id: int
    dest_dir: str


class RenameBody(BaseModel):
    file_id: int
    new_name: str


class DeleteBody(BaseModel):
    file_id: int
    confirm: bool = False


class OpenFolderBody(BaseModel):
    path: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/open-folder")
def open_folder(body: OpenFolderBody):
    """Open a folder in the native file manager."""
    path = body.path.strip().rstrip("\\/")
    if os.path.isfile(path):
        path = os.path.dirname(path)

    try:
        if sys.platform == "win32":
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
        if HOST_AGENT_URL:
            result = _agent_post("/file/move", {"src": rec.full_path, "dest_dir": body.dest_dir})
            new_path = result["new_path"]
        else:
            new_path = move_file(rec.full_path, body.dest_dir)
    except (FileOperationError, Exception) as exc:
        raise HTTPException(400, str(exc)) from exc

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
        if HOST_AGENT_URL:
            result = _agent_post("/file/rename", {"src": rec.full_path, "new_name": body.new_name})
            new_path = result["new_path"]
        else:
            new_path = rename_file(rec.full_path, body.new_name)
    except (FileOperationError, Exception) as exc:
        raise HTTPException(400, str(exc)) from exc

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
        if HOST_AGENT_URL:
            _agent_post("/file/delete", {"path": rec.full_path})
        else:
            delete_file(rec.full_path)
    except (FileOperationError, Exception) as exc:
        raise HTTPException(400, str(exc)) from exc

    db.delete(rec)
    db.commit()
    return {"message": "File deleted."}


def _get_or_404(db: Session, file_id: int) -> FileRecord:
    rec = db.get(FileRecord, file_id)
    if not rec:
        raise HTTPException(404, "File not found.")
    return rec
