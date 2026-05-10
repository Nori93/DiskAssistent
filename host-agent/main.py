"""
Host Agent — main FastAPI application.

Exposes a local HTTP API for all filesystem operations so that containerised
services (WebAPI, Worker) can perform file I/O on the host without bind-mounts.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import AGENT_SECRET, APP_HOST, APP_PORT, logger
from routers import archive, dedup, filesystem

app = FastAPI(
    title="DiskAssistent Host Agent",
    version="1.0.0",
    description="Native host-side filesystem API for DiskAssistent containers.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Optional bearer-token auth ────────────────────────────────────────────────


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if AGENT_SECRET and request.url.path not in ("/health", "/"):
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {AGENT_SECRET}":
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    import platform

    return {"status": "ok", "os": platform.system(), "version": "1.0.0"}


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(filesystem.router)
app.include_router(archive.router)
app.include_router(dedup.router)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Host Agent on %s:%s", APP_HOST, APP_PORT)
    uvicorn.run("main:app", host=APP_HOST, port=APP_PORT, reload=False)
