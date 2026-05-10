"""
Host Agent HTTP client helpers for the Worker Service.

When HOST_AGENT_URL is set, all filesystem operations are delegated to the
native Host Agent running on the host OS instead of being performed locally.
This allows the Worker Service to run in a container without bind-mounted drives.
"""

from __future__ import annotations

from config import HOST_AGENT_SECRET, HOST_AGENT_URL


def enabled() -> bool:
    """Return True when the Host Agent is configured."""
    return bool(HOST_AGENT_URL)


def headers() -> dict[str, str]:
    if HOST_AGENT_SECRET:
        return {"Authorization": f"Bearer {HOST_AGENT_SECRET}"}
    return {}


def get(endpoint: str, **params) -> dict:
    import httpx

    url = f"{HOST_AGENT_URL}{endpoint}"
    resp = httpx.get(url, params=params, headers=headers(), timeout=60.0)
    resp.raise_for_status()
    return resp.json()


def post(endpoint: str, data: dict, timeout: float = 600.0) -> dict:
    import httpx

    url = f"{HOST_AGENT_URL}{endpoint}"
    resp = httpx.post(url, json=data, headers=headers(), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def path_exists(path: str) -> bool:
    return post("/file/exists", {"path": path})["exists"]


def stream_scan(root_path: str):
    """Yield file-record dicts from the agent's NDJSON scan stream."""
    import datetime
    import json

    import httpx

    url = f"{HOST_AGENT_URL}/scan/stream"
    with httpx.Client(timeout=3600.0) as client:
        with client.stream("POST", url, json={"path": root_path}, headers=headers()) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    record = json.loads(line)
                    record["created_at"] = datetime.datetime.fromisoformat(record["created_at"])
                    record["modified_at"] = datetime.datetime.fromisoformat(record["modified_at"])
                    yield record
