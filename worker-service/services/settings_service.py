from __future__ import annotations
"""
Application settings service – persists user preferences in settings.json.
"""

import json
from pathlib import Path

from config import BASE_DIR, logger

SETTINGS_PATH = Path(__file__).parent.parent.parent / "settings.json"

_DEFAULTS: dict = {
    "archive_dir": "",       # Path where compressed game archives are stored
    "dedup_shared_dir": "", # Path where canonical shared DLL copies are stored
}


def load_settings() -> dict:
    """Return current settings, falling back to defaults for missing keys."""
    if not SETTINGS_PATH.exists():
        return dict(_DEFAULTS)
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except Exception as exc:
        logger.warning("Could not read settings.json: %s", exc)
        return dict(_DEFAULTS)


def save_settings(updates: dict) -> dict:
    """Merge *updates* into current settings, persist, and return full settings."""
    settings = load_settings()
    settings.update(updates)
    try:
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.error("Could not write settings.json: %s", exc)
        raise
    return settings

