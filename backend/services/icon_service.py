"""
icon_service.py — extract the icon from a game's .exe and save as PNG.

Strategy (Windows-only):
  1. Find the "best" .exe for a group (root-level, largest, or name-matching).
  2. Use PowerShell + .NET System.Drawing to extract the associated icon.
  3. Save as PNG into THUMBNAILS_DIR / group_{id}.png.
  4. Return the web-accessible URL path, or None on failure.

On non-Windows or if extraction fails the function returns None silently so
the caller can fall back to the emoji icon.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from backend.config import IS_WINDOWS, THUMBNAILS_DIR, logger

# Web path prefix that maps to THUMBNAILS_DIR via the /static mount
THUMBS_URL_PREFIX = "/static/img/thumbnails"

# PowerShell one-liner: extract icon → save PNG
_PS_EXTRACT = r"""
param($exe, $out)
Add-Type -AssemblyName System.Drawing
try {
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exe)
    if (-not $icon) { exit 1 }
    $bmp = $icon.ToBitmap()
    $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    $icon.Dispose(); $bmp.Dispose()
    exit 0
} catch { exit 1 }
"""


def extract_group_icon(group_id: int, exe_path: str) -> Optional[str]:
    """Extract the icon from *exe_path* and store it as group_{group_id}.png.

    Returns the URL path (``/static/img/thumbnails/group_<id>.png``) on
    success, or ``None`` if extraction failed or we are not on Windows.
    """
    if not IS_WINDOWS:
        return None

    if not os.path.isfile(exe_path):
        logger.debug("icon_service: exe not found: %s", exe_path)
        return None

    out_path = THUMBNAILS_DIR / f"group_{group_id}.png"

    # Write the PS script to a fixed path (no atexit registration unlike NamedTemporaryFile)
    ps1_path = THUMBNAILS_DIR / f"_icon_extract_{group_id}.ps1"
    try:
        ps1_path.write_text(_PS_EXTRACT, encoding="utf-8")

        result = subprocess.run(
            [
                "powershell.exe",
                "-NonInteractive",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", str(ps1_path),
                "-exe",  exe_path,
                "-out",  str(out_path),
            ],
            capture_output=True,
            timeout=15,
        )

        if result.returncode != 0:
            logger.debug(
                "icon_service: PS extraction failed for group %d (%s): %s",
                group_id, exe_path,
                result.stderr.decode(errors="replace").strip(),
            )
            return None

        url = f"{THUMBS_URL_PREFIX}/group_{group_id}.png"
        logger.info("icon_service: saved icon for group %d → %s", group_id, url)
        return url

    except RuntimeError as exc:
        # Interpreter is shutting down (e.g. uvicorn reload) — skip silently
        logger.debug("icon_service: skipped during shutdown: %s", exc)
        return None
    except Exception as exc:
        logger.debug("icon_service: exception for group %d: %s", group_id, exc)
        return None
    finally:
        try:
            ps1_path.unlink(missing_ok=True)
        except Exception:
            pass


def pick_best_exe(db, group_id: int, root_path: str) -> Optional[str]:
    """Return the full_path of the most representative .exe in a group.

    Priority order:
      1. Exact stem match with group folder name (e.g. "holehouse" == "holehouse").
      2. Best fuzzy match by difflib similarity (≥ 0.6) — catches "HouseFlipperGame" for "House Flipper".
      3. Largest .exe at the root level of the group.
      4. Largest .exe anywhere in the group.
    """
    import difflib
    from database.models import FileRecord

    folder_name = Path(root_path).name.lower()
    sep         = os.sep
    clean_root  = root_path.rstrip(sep)

    all_exes = (
        db.query(FileRecord)
        .filter(
            FileRecord.group_id == group_id,
            FileRecord.extension == ".exe",
        )
        .order_by(FileRecord.size_bytes.desc())
        .all()
    )

    if not all_exes:
        return None

    # 1. Exact stem match
    for f in all_exes:
        if Path(f.full_path).stem.lower() == folder_name:
            return f.full_path

    # 2. Fuzzy match — pick the exe stem most similar to the folder name
    def _similarity(f) -> float:
        stem = Path(f.full_path).stem.lower()
        # Strip common suffixes that reduce similarity: -win64, _release, _launcher…
        import re
        stem_clean = re.sub(r'[-_](win64|win32|x64|x86|release|debug|launcher|game|app)$', '', stem)
        return difflib.SequenceMatcher(None, folder_name, stem_clean).ratio()

    best = max(all_exes, key=_similarity)
    if _similarity(best) >= 0.6:
        return best.full_path

    # 3. Root-level, largest
    root_exes = [
        f for f in all_exes
        if f.parent_dir.rstrip(sep).lower() == clean_root.lower()
    ]
    if root_exes:
        return root_exes[0].full_path    # already sorted desc by size

    # 4. Any exe, largest
    return all_exes[0].full_path
