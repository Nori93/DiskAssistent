"""
Disk / filesystem API endpoints.
"""
from fastapi import APIRouter, HTTPException

from services.scanner import get_available_disks, get_directory_tree

router = APIRouter(prefix="/api/disks", tags=["Disks"])


@router.get("/")
def list_disks():
    """Return all available disks with usage information."""
    return get_available_disks()


@router.get("/tree")
def directory_tree(path: str, depth: int = 2):
    """Return a recursive folder tree for *path*."""
    if depth > 5:
        raise HTTPException(400, "Maximum tree depth is 5")
    return get_directory_tree(path, depth)
