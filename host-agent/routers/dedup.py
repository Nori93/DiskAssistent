"""
Dedup router — DLL scanning, zip backup, hardlink/copy operations.
Used by the Worker container to perform all dedup filesystem operations
on the host without needing bind-mounted drives.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import logger

router = APIRouter()

DLL_EXTENSIONS = {".dll", ".so", ".dylib"}


# ── DLL scanning ──────────────────────────────────────────────────────────────


class ScanDllsRequest(BaseModel):
    root_path: str


@router.post("/dedup/scan-dlls")
def scan_dlls(body: ScanDllsRequest):
    """Walk *root_path* and return metadata + SHA-256 for every DLL file found."""
    root = Path(body.root_path)
    if not root.exists():
        raise HTTPException(400, f"Path not found: {root}")

    results = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in DLL_EXTENSIONS:
            try:
                sha256 = _sha256(p)
                results.append({
                    "path": str(p),
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                    "sha256": sha256,
                })
            except OSError:
                pass
    return results


# ── DLL zip backup ────────────────────────────────────────────────────────────


class ZipFileRequest(BaseModel):
    src_path: str
    zip_path: str


@router.post("/dedup/zip-file")
def zip_single_file(body: ZipFileRequest):
    """Create a zip containing one file at *zip_path*. No-op if zip already exists."""
    src = Path(body.src_path)
    dst = Path(body.zip_path)

    if dst.exists():
        return {"zip_path": str(dst), "created": False}

    if not src.exists():
        raise HTTPException(400, f"Source not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(str(dst), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.write(str(src), src.name)
    except Exception as exc:
        raise HTTPException(500, f"Zip failed: {exc}") from exc

    return {"zip_path": str(dst), "created": True}


# ── Hardlink / copy ───────────────────────────────────────────────────────────


class LinkOrCopyRequest(BaseModel):
    src: str
    dst: str  # full destination path including filename


@router.post("/dedup/link-or-copy")
def link_or_copy(body: LinkOrCopyRequest):
    """Create a hardlink from *src* to *dst*; fall back to copy if cross-device."""
    src = Path(body.src)
    dst = Path(body.dst)

    if not src.exists():
        raise HTTPException(400, f"Source not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    method = "copy"
    try:
        src_dev = src.stat().st_dev
        dst_dev = dst.parent.stat().st_dev
        if src_dev == dst_dev:
            os.link(src, dst)
            method = "hardlink"
        else:
            shutil.copy2(src, dst)
    except OSError:
        shutil.copy2(src, dst)

    logger.info("link-or-copy (%s): %s → %s", method, src, dst)
    return {"method": method, "dst": str(dst)}


# ── Extract DLL zip (for restore) ─────────────────────────────────────────────


class ExtractZipRequest(BaseModel):
    zip_path: str
    dst_dir: str


@router.post("/dedup/restore-dll")
def restore_dll(body: ExtractZipRequest):
    """Extract a single-file DLL zip to *dst_dir* (used during group restore)."""
    zp = Path(body.zip_path)
    if not zp.exists():
        raise HTTPException(404, f"DLL zip not found: {zp}")

    dst = Path(body.dst_dir)
    dst.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zp, "r") as zf:
            zf.extractall(dst)
    except Exception as exc:
        raise HTTPException(500, f"DLL restore failed: {exc}") from exc

    return {"extracted_to": str(dst)}


# ── Internal helpers ───────────────────────────────────────────────────────────


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()
