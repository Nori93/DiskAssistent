"""
File operations service: move, rename, delete with safety checks.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from backend.config import logger


class FileOperationError(Exception):
    """Raised when a file operation cannot be completed safely."""


def move_file(src: str, dest_dir: str) -> str:
    """
    Move *src* into *dest_dir*.  Returns the new full path.
    Raises FileOperationError on any failure.
    """
    src_path  = Path(src)
    dest_path = Path(dest_dir)

    if not src_path.exists():
        raise FileOperationError(f"Source file not found: {src}")
    if not dest_path.is_dir():
        raise FileOperationError(f"Destination is not a directory: {dest_dir}")

    new_path = dest_path / src_path.name

    # Avoid accidental overwrites
    if new_path.exists():
        raise FileOperationError(
            f"A file named '{src_path.name}' already exists in '{dest_dir}'."
        )

    try:
        shutil.move(str(src_path), str(new_path))
        logger.info("Moved: %s → %s", src, new_path)
        return str(new_path)
    except Exception as exc:
        raise FileOperationError(f"Move failed: {exc}") from exc


def rename_file(src: str, new_name: str) -> str:
    """
    Rename *src* to *new_name* (just the filename, not a full path).
    Returns the new full path.
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileOperationError(f"File not found: {src}")

    # Sanitise new name
    new_name = new_name.strip()
    if not new_name or any(c in new_name for c in r'\/:*?"<>|'):
        raise FileOperationError("Invalid file name.")

    new_path = src_path.parent / new_name
    if new_path.exists():
        raise FileOperationError(f"A file named '{new_name}' already exists.")

    try:
        src_path.rename(new_path)
        logger.info("Renamed: %s → %s", src, new_path)
        return str(new_path)
    except Exception as exc:
        raise FileOperationError(f"Rename failed: {exc}") from exc


def delete_file(src: str) -> None:
    """
    Permanently delete *src*.
    NOTE: The API layer must confirm with the user before calling this.
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileOperationError(f"File not found: {src}")

    try:
        if src_path.is_dir():
            shutil.rmtree(src_path)
            logger.info("Deleted directory: %s", src)
        else:
            src_path.unlink()
            logger.info("Deleted file: %s", src)
    except Exception as exc:
        raise FileOperationError(f"Delete failed: {exc}") from exc
