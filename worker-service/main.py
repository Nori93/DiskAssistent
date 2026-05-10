"""
Worker Service — FastAPI application entry point.
Handles all heavy processing on port 8002:
  - Disk scanning (scan, rescan-all)
  - Archive / restore game groups
  - DLL deduplication
  - File recategorization + regrouping
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "database-service"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_PORT, APP_TITLE, APP_VERSION, logger
from diskassistent_db.models import init_db

init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.scan_service import resume_interrupted_scans
    resume_interrupted_scans()
    logger.info("Worker Service started on port %s", APP_PORT)
    yield


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Heavy background processing for DiskAssistent.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import archive, dedup, recategorize, scan  # noqa: E402

app.include_router(scan.router)
app.include_router(archive.router)
app.include_router(dedup.router)
app.include_router(recategorize.router)


@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools():
    return {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "worker", "version": APP_VERSION}
