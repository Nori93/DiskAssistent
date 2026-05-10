"""
Archive router — create/restore zip archives and delete directory trees.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import logger

router = APIRouter()


class ZipCreateRequest(BaseModel):
    root_path: str
    zip_path: str
    exclude_paths: list[str] = []
    dll_manifest_json: str = ""


@router.post("/archive/create")
def archive_create(body: ZipCreateRequest):
    """Zip *root_path* to *zip_path*, skipping *exclude_paths*, embedding dll manifest."""
    root = Path(body.root_path)
    if not root.exists():
        raise HTTPException(400, f"Root path not found: {root}")

    zip_path = Path(body.zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    exclude = {Path(p) for p in body.exclude_paths}
    all_files = [p for p in root.rglob("*") if p.is_file() and p not in exclude]
    total = len(all_files)

    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for fp in all_files:
                zf.write(fp, fp.relative_to(root.parent))
            if body.dll_manifest_json:
                zf.writestr("_dlls.json", body.dll_manifest_json)
    except Exception as exc:
        raise HTTPException(500, f"Zip creation failed: {exc}") from exc

    size = zip_path.stat().st_size
    logger.info("Created archive: %s (%d files, %.1f MB)", zip_path, total, size / 1e6)
    return {"zip_path": str(zip_path), "size_bytes": size, "file_count": total}


class ZipRestoreRequest(BaseModel):
    zip_path: str
    extract_to: str


@router.post("/archive/restore")
def archive_restore(body: ZipRestoreRequest):
    """Extract *zip_path* to *extract_to*; returns embedded dll_entries list."""
    zip_path = Path(body.zip_path)
    if not zip_path.exists():
        raise HTTPException(400, f"Archive not found: {zip_path}")

    extract_to = Path(body.extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    dll_entries: list[dict] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "_dlls.json" in zf.namelist():
                dll_entries = json.loads(zf.read("_dlls.json").decode("utf-8")).get("dlls", [])
            members = [m for m in zf.namelist() if m != "_dlls.json"]
            for member in members:
                zf.extract(member, extract_to)
    except Exception as exc:
        raise HTTPException(500, f"Extraction failed: {exc}") from exc

    logger.info("Restored archive: %s → %s (%d files)", zip_path, extract_to, len(members))
    return {"dll_entries": dll_entries, "members_count": len(members)}


class DeleteTreeRequest(BaseModel):
    path: str


@router.post("/file/delete-tree")
def delete_tree(body: DeleteTreeRequest):
    """Recursively delete a directory tree."""
    p = Path(body.path)
    if not p.exists():
        raise HTTPException(404, f"Path not found: {p}")
    try:
        shutil.rmtree(p)
        logger.info("Deleted tree: %s", p)
        return {"deleted": str(p)}
    except Exception as exc:
        raise HTTPException(500, f"Delete-tree failed: {exc}") from exc
