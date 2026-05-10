"""
DiskAssistent — main FastAPI application entry point.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path so `backend`, `database`, `ai` are importable
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.config import APP_TITLE, APP_VERSION, logger
from database.models import init_db

# ── Database init ─────────────────────────────────────────────────────────────
init_db()


# ── Lifespan: resume any interrupted scan jobs on startup ─────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.services.scan_service import resume_interrupted_scans

    resume_interrupted_scans()
    yield


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Manage, categorize, and organize files across multiple disks.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files & templates ──────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR / "static"),
    name="static",
)
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

# ── API routers ───────────────────────────────────────────────────────────────
# init_db() must run before routers are imported — E402 is intentional here
from backend.routers import archive, dedup, disks, files, groups, operations, scan  # noqa: E402

app.include_router(disks.router)
app.include_router(scan.router)
app.include_router(files.router)
app.include_router(operations.router)
app.include_router(groups.router)
app.include_router(archive.router)
app.include_router(dedup.router)

# ── No-cache middleware for static JS/CSS (dev convenience) ──────────────────
@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    response: Response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ── Frontend route ────────────────────────────────────────────────────────────


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/img/favicon.svg")


@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools():
    """Suppress Chrome DevTools discovery 404 logs."""
    return {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": APP_TITLE})


@app.get("/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}


logger.info("DiskAssistent application ready.")
