"""
File system scanning service.
Cross-platform: handles Windows drive letters and Linux mount points.
"""

from __future__ import annotations

import datetime
import os
from collections.abc import Iterator
from pathlib import Path

from config import IS_WINDOWS, logger


def get_available_disks() -> list[dict]:
    """
    Return a list of available disks/mount points on the current OS.
    """
    disks = []

    if IS_WINDOWS:
        import ctypes
        import string

        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                root = f"{letter}:\\"
                try:
                    total, used, free = _win_disk_usage(root)
                    disks.append(
                        {
                            "path": root,
                            "label": letter,
                            "total_bytes": total,
                            "used_bytes": used,
                            "free_bytes": free,
                            "total_human": _human(total),
                            "used_human": _human(used),
                            "free_human": _human(free),
                            "pct_used": round(used / total * 100, 1) if total else 0,
                        }
                    )
                except Exception:
                    pass
            bitmask >>= 1
    else:
        # Linux/macOS: parse /proc/mounts or use psutil
        try:
            import psutil  # type: ignore

            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append(
                        {
                            "path": part.mountpoint,
                            "label": part.device,
                            "total_bytes": usage.total,
                            "used_bytes": usage.used,
                            "free_bytes": usage.free,
                            "total_human": _human(usage.total),
                            "used_human": _human(usage.used),
                            "free_human": _human(usage.free),
                            "pct_used": round(usage.percent, 1),
                        }
                    )
                except PermissionError:
                    pass
        except ImportError:
            # Fallback without psutil
            disks.append(
                {
                    "path": "/",
                    "label": "root",
                    "total_bytes": 0,
                    "used_bytes": 0,
                    "free_bytes": 0,
                    "total_human": "?",
                    "used_human": "?",
                    "free_human": "?",
                    "pct_used": 0,
                }
            )

    return disks


def scan_directory(root: str) -> Iterator[dict]:
    """
    Recursively scan *root* and yield one dict per file.
    Yields dicts with metadata; never raises â€” errors are logged and skipped.
    """
    root_path = Path(root)
    if not root_path.exists():
        logger.warning("Scan root does not exist: %s", root)
        return

    logger.info("Starting scan of: %s", root)

    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        # Skip hidden/system directories on Windows
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


def get_directory_tree(path: str, depth: int = 2) -> list[dict]:
    """
    Return a lightweight recursive directory tree (folders only) up to *depth*.
    Used by the frontend tree view.
    """
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return []
    return _tree_node(root, depth)


# â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_SYSTEM_DIRS = {
    "$recycle.bin",
    "system volume information",
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "recovery",
    "boot",
    "proc",
    "sys",
    "dev",
    "run",
}


def _is_system_dir(path: Path) -> bool:
    return path.name.lower() in _SYSTEM_DIRS or path.name.startswith(".")


def _get_ctime(stat: os.stat_result) -> float:
    # On Linux st_ctime is the last metadata change, not creation time.
    # st_birthtime exists on macOS/BSD; fall back to st_mtime.
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


def _tree_node(path: Path, depth: int) -> list[dict]:
    if depth == 0:
        return []
    nodes = []
    try:
        for child in sorted(path.iterdir()):
            if child.is_dir() and not _is_system_dir(child):
                nodes.append(
                    {
                        "name": child.name,
                        "path": str(child),
                        "children": _tree_node(child, depth - 1),
                    }
                )
    except PermissionError:
        pass
    return nodes

