"""
Application configuration and cross-platform utilities.
"""
import logging
import os
import platform
from pathlib import Path

# ── Logging Setup ─────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("diskassistent")

# ── OS Detection ──────────────────────────────────────────────────────────────

CURRENT_OS = platform.system()   # "Windows" | "Linux" | "Darwin"
IS_WINDOWS = CURRENT_OS == "Windows"
IS_LINUX   = CURRENT_OS == "Linux"

logger.info("Detected OS: %s", CURRENT_OS)

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR      = Path(__file__).parent.parent
DB_PATH       = BASE_DIR / "database" / "diskassistent.db"
THUMBNAILS_DIR = BASE_DIR / "frontend" / "static" / "img" / "thumbnails"
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

# ── App Settings ──────────────────────────────────────────────────────────────

APP_TITLE   = "DiskAssistent"
APP_VERSION = "1.0.0"
APP_HOST    = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT    = int(os.getenv("APP_PORT", "8000"))

# Max file size shown in scan (bytes); set to 0 to disable filtering
MAX_SCAN_SIZE = 0

# Extensions considered as media/image for thumbnail generation
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"}
DOC_EXTENSIONS   = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".md", ".ppt", ".pptx"}

# ── AI backend (optional) ────────────────────────────────────────────────────
# Set OPENAI_API_KEY to use the OpenAI cloud API.
# Set AI_BASE_URL to point at a local server instead:
#   Ollama:    AI_BASE_URL=http://localhost:11434/v1   AI_MODEL=llama3
#   LM Studio: AI_BASE_URL=http://localhost:1234/v1    AI_MODEL=local-model
# When AI_BASE_URL is set, OPENAI_API_KEY is sent as-is (Ollama accepts any value).
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_BASE_URL    = os.getenv("AI_BASE_URL", "")      # empty = use OpenAI cloud
AI_MODEL       = os.getenv("AI_MODEL", "gpt-3.5-turbo")
