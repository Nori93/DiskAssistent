"""
Filesystem router — disk listing, directory tree, file scanning,
and basic file operations (move / rename / delete).
"""

from __future__ import annotations

import datetime
import json
import os
import platform
import shutil
import string
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import logger

router = APIRouter()

# ── Constants ─────────────────────────────────────────────────────────────────

IS_WINDOWS = platform.system() == "Windows"

_SYSTEM_DIRS = {
    "$recycle.bin", "system volume information", "windows",
    "program files", "program files (x86)", "programdata",
    "recovery", "boot", "proc", "sys", "dev", "run",
}


# ── Disk listing ──────────────────────────────────────────────────────────────


@router.get("/disks")
def list_disks():
    """Return all available disks/mount-points with usage stats."""
    return _get_disks()


# ── Directory tree ─────────────────────────────────────────────────────────────


@router.get("/tree")
def directory_tree(path: str, depth: int = 2):
    if depth > 5:
        raise HTTPException(400, "Maximum tree depth is 5")
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return []
    return _tree_node(root, depth)


# ── File scanning (NDJSON stream) ─────────────────────────────────────────────


class ScanRequest(BaseModel):
    path: str


@router.post("/scan/stream")
def scan_stream(body: ScanRequest):
    """Stream file metadata records as NDJSON (one JSON object per line)."""
    def _generate():
        for record in _scan_directory(body.path):
            record["created_at"] = record["created_at"].isoformat()
            record["modified_at"] = record["modified_at"].isoformat()
            yield json.dumps(record) + "\n"

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


# ── File operations ────────────────────────────────────────────────────────────


class PathBody(BaseModel):
    path: str


class MoveBody(BaseModel):
    src: str
    dest_dir: str


class RenameBody(BaseModel):
    src: str
    new_name: str


@router.post("/file/exists")
def file_exists(body: PathBody):
    return {"exists": Path(body.path).exists()}


@router.post("/file/move")
def move_file(body: MoveBody):
    src = Path(body.src)
    dst_dir = Path(body.dest_dir)
    if not src.exists():
        raise HTTPException(400, f"Source not found: {body.src}")
    if not dst_dir.is_dir():
        raise HTTPException(400, f"Destination is not a directory: {body.dest_dir}")
    new_path = dst_dir / src.name
    if new_path.exists():
        raise HTTPException(400, f"'{src.name}' already exists in destination.")
    try:
        shutil.move(str(src), str(new_path))
        logger.info("Moved: %s → %s", src, new_path)
        return {"new_path": str(new_path)}
    except Exception as exc:
        raise HTTPException(500, f"Move failed: {exc}") from exc


@router.post("/file/rename")
def rename_file(body: RenameBody):
    src = Path(body.src)
    if not src.exists():
        raise HTTPException(400, f"File not found: {body.src}")
    name = body.new_name.strip()
    if not name or any(c in name for c in r'\/:*?"<>|'):
        raise HTTPException(400, "Invalid file name.")
    new_path = src.parent / name
    if new_path.exists():
        raise HTTPException(400, f"'{name}' already exists.")
    try:
        src.rename(new_path)
        logger.info("Renamed: %s → %s", src, new_path)
        return {"new_path": str(new_path)}
    except Exception as exc:
        raise HTTPException(500, f"Rename failed: {exc}") from exc


@router.post("/file/delete")
def delete_path(body: PathBody):
    """Delete a file or directory (recursively)."""
    p = Path(body.path)
    if not p.exists():
        raise HTTPException(404, f"Path not found: {body.path}")
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        logger.info("Deleted: %s", p)
        return {"deleted": str(p)}
    except Exception as exc:
        raise HTTPException(500, f"Delete failed: {exc}") from exc


# ── Internal helpers ───────────────────────────────────────────────────────────


def _get_disks() -> list[dict]:
    disks: list[dict] = []
    if IS_WINDOWS:
        import ctypes

        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                root = f"{letter}:\\"
                try:
                    total, used, free = _win_disk_usage(root)
                    disks.append({
                        "path": root,
                        "label": letter,
                        "total_bytes": total,
                        "used_bytes": used,
                        "free_bytes": free,
                        "total_human": _human(total),
                        "used_human": _human(used),
                        "free_human": _human(free),
                        "pct_used": round(used / total * 100, 1) if total else 0,
                    })
                except Exception:
                    pass
            bitmask >>= 1
    else:
        try:
            import psutil  # type: ignore

            for part in psutil.disk_partitions(all=False):
                try:
                    u = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "path": part.mountpoint,
                        "label": part.device,
                        "total_bytes": u.total,
                        "used_bytes": u.used,
                        "free_bytes": u.free,
                        "total_human": _human(u.total),
                        "used_human": _human(u.used),
                        "free_human": _human(u.free),
                        "pct_used": round(u.percent, 1),
                    })
                except PermissionError:
                    pass
        except ImportError:
            disks.append({
                "path": "/", "label": "root",
                "total_bytes": 0, "used_bytes": 0, "free_bytes": 0,
                "total_human": "?", "used_human": "?", "free_human": "?",
                "pct_used": 0,
            })
    return disks


def _scan_directory(root: str) -> Iterator[dict]:
    root_path = Path(root)
    if not root_path.exists():
        logger.warning("Scan root does not exist: %s", root)
        return
    logger.info("Agent scanning: %s", root)
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        dirnames[:] = [d for d in dirnames if not _is_system_dir(Path(dirpath) / d)]
        for filename in filenames:
            full_path = Path(dirpath) / filename
            try:
                stat = full_path.stat()
                yield {
                    "name": filename,
                    "full_path": str(full_path),
                    "parent_dir": str(full_path.parent),
                    "extension": full_path.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.datetime.fromtimestamp(
                        _get_ctime(stat), tz=datetime.timezone.utc
                    ).replace(tzinfo=None),
                    "modified_at": datetime.datetime.fromtimestamp(
                        stat.st_mtime, tz=datetime.timezone.utc
                    ).replace(tzinfo=None),
                }
            except (PermissionError, OSError) as exc:
                logger.debug("Skipping %s: %s", full_path, exc)


def _tree_node(path: Path, depth: int) -> list[dict]:
    if depth == 0:
        return []
    nodes = []
    try:
        for child in sorted(path.iterdir()):
            if child.is_dir() and not _is_system_dir(child):
                nodes.append({
                    "name": child.name,
                    "path": str(child),
                    "children": _tree_node(child, depth - 1),
                })
    except PermissionError:
        pass
    return nodes


def _is_system_dir(path: Path) -> bool:
    return path.name.lower() in _SYSTEM_DIRS or path.name.startswith(".")


def _get_ctime(stat: os.stat_result) -> float:
    return getattr(stat, "st_birthtime", stat.st_ctime)


def _win_disk_usage(drive: str):
    import ctypes

    free_user = ctypes.c_ulonglong(0)
    total = ctypes.c_ulonglong(0)
    free_total = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        drive,
        ctypes.byref(free_user),
        ctypes.byref(total),
        ctypes.byref(free_total),
    )
    used = total.value - free_total.value
    return total.value, used, free_total.value


def _human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
