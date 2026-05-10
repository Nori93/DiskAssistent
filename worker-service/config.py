"""
Worker Service — configuration.
"""

import logging
import os
import platform
from pathlib import Path

_ROOT = Path(__file__).parent.parent
LOG_DIR = _ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "worker.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("worker")

CURRENT_OS = platform.system()
IS_WINDOWS = CURRENT_OS == "Windows"
IS_LINUX = CURRENT_OS == "Linux"

BASE_DIR = _ROOT
THUMBNAILS_DIR = _ROOT.parent / "frontend" / "dist" / "assets" / "thumbnails"
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

APP_TITLE = "DiskAssistent Worker Service"
APP_VERSION = "2.0.0"
APP_HOST = os.getenv("WORKER_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("WORKER_PORT", "8002"))

# Host Agent URL — set this when running in a container so that filesystem
# operations are delegated to the native Host Agent running on the host OS.
# Example: http://host.containers.internal:8003
# Leave empty to use local filesystem access (native / dev mode).
HOST_AGENT_URL = os.getenv("HOST_AGENT_URL", "").rstrip("/")
HOST_AGENT_SECRET = os.getenv("HOST_AGENT_SECRET", "")

MAX_SCAN_SIZE = 0
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"}
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".md", ".ppt", ".pptx"}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "")  # empty = use OpenAI cloud
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
