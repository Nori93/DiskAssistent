"""
Disk / filesystem API endpoints.
"""

from fastapi import APIRouter, HTTPException

from config import HOST_AGENT_SECRET, HOST_AGENT_URL
from services.scanner import get_available_disks, get_directory_tree

router = APIRouter(prefix="/api/disks", tags=["Disks"])


def _agent_get(endpoint: str, **params):
    import httpx

    headers = {"Authorization": f"Bearer {HOST_AGENT_SECRET}"} if HOST_AGENT_SECRET else {}
    resp = httpx.get(f"{HOST_AGENT_URL}{endpoint}", params=params, headers=headers, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


@router.get("/")
def list_disks():
    """Return all available disks with usage information."""
    if HOST_AGENT_URL:
        return _agent_get("/disks")
    return get_available_disks()


@router.get("/tree")
def directory_tree(path: str, depth: int = 2):
    """Return a recursive folder tree for *path*."""
    if depth > 5:
        raise HTTPException(400, "Maximum tree depth is 5")
    if HOST_AGENT_URL:
        return _agent_get("/tree", path=path, depth=depth)
    return get_directory_tree(path, depth)
