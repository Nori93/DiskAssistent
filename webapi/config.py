"""
WebAPI — configuration.
"""
import logging
import os
import platform
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
LOG_DIR = _ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "webapi.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("webapi")

# ── OS Detection ──────────────────────────────────────────────────────────────
CURRENT_OS = platform.system()
IS_WINDOWS = CURRENT_OS == "Windows"
IS_LINUX = CURRENT_OS == "Linux"

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = _ROOT
THUMBNAILS_DIR = _ROOT.parent / "frontend" / "dist" / "assets" / "thumbnails"
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

# ── App Settings ──────────────────────────────────────────────────────────────
APP_TITLE = "DiskAssistent WebAPI"
APP_VERSION = "2.0.0"
APP_HOST = os.getenv("WEBAPI_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("WEBAPI_PORT", "8001"))

# Worker service base URL (for proxying heavy operations)
WORKER_URL = os.getenv("WORKER_URL", "http://localhost:8002")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"}
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".md", ".ppt", ".pptx"}
