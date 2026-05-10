"""
WebAPI — FastAPI application entry point.
Serves the Angular frontend's REST API calls on port 8001.
Heavy processing (scan, archive, dedup, recategorize) is proxied
to the Worker Service on port 8002.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "database-service"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import APP_PORT, APP_TITLE, APP_VERSION, WORKER_URL, logger
from diskassistent_db.models import init_db

init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(base_url=WORKER_URL, timeout=300.0)
    logger.info("WebAPI started. Worker proxy → %s", WORKER_URL)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="REST API for DiskAssistent Angular frontend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from routers import disks, files, groups, operations  # noqa: E402

app.include_router(disks.router)
app.include_router(files.router)
app.include_router(groups.router)
app.include_router(operations.router)


# ── Proxy: forward heavy-processing routes to Worker Service ──────────────────
_PROXIED_PREFIXES = (
    "/api/scan",
    "/api/archive",
    "/api/dedup",
)


@app.api_route(
    "/api/scan/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
@app.api_route(
    "/api/archive/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
@app.api_route(
    "/api/dedup/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def proxy_to_worker(request: Request, path: str):
    """Transparent reverse proxy for heavy-processing endpoints."""
    client: httpx.AsyncClient = request.app.state.http
    url = str(request.url).replace(str(request.base_url).rstrip("/"), "")
    body = await request.body()
    try:
        resp = await client.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=body,
        )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type"),
        )
    except httpx.ConnectError:
        return JSONResponse(
            {"detail": "Worker Service unavailable. Start worker-service on port 8002."},
            status_code=503,
        )


# ── Well-known / favicon ──────────────────────────────────────────────────────
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/static/img/favicon.svg")


@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools():
    return {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "webapi", "version": APP_VERSION}


logger.info("WebAPI ready on port %s", APP_PORT)
