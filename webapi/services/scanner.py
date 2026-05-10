"""
File system scanning service — disk listing and directory tree.
(Lightweight operations only; full recursive scan is in worker-service.)
"""

from __future__ import annotations

from pathlib import Path

from config import IS_WINDOWS


def get_available_disks() -> list[dict]:
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
        try:
            import psutil

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
            disks.append(
                {
                    "path": "/",
                    "label": "root",
                    "total_bytes": 0,
                    "used_bytes": 0,
                    "free_bytes": 0,
                    "pct_used": 0,
                }
            )

    return disks


def get_directory_tree(path: str, depth: int = 2) -> list[dict]:
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return []
    return _tree_node(root, depth)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
