"""
Database configuration for diskassistent_db.
Reads DB_PATH from the environment variable DISKASSISTENT_DB_PATH,
defaulting to <repo-root>/database/diskassistent.db.
"""

import logging
import os
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_DIR = Path(os.getenv("LOG_DIR", Path(__file__).parent.parent.parent / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("diskassistent")

# ── Database path ─────────────────────────────────────────────────────────────

_default_db = Path(__file__).parent.parent.parent / "database" / "diskassistent.db"
DB_PATH = Path(os.getenv("DISKASSISTENT_DB_PATH", str(_default_db)))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
