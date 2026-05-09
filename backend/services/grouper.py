"""
Group detection service.

Strategy:
  1. Deep-scan all subdirectories to find every "leaf" directory
     (a folder that directly contains files).
  2. For each leaf, bubble UP through generic sub-folder names
     (bin, data, scripts, x64, …) until we reach a meaningful
     named folder — that becomes the group root.
  3. Deduplicate and aggregate extensions across all leaves that
     share the same group root.
  4. Categorise each group root using its name + combined extensions.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from ai.categorizer import categorize_folder

# ── Generic sub-folder names ──────────────────────────────────────────────────
# Folders with these names are internal parts of a larger unit, NOT the unit
# itself — so we bubble up past them when searching for the group root.
_GENERIC = {
    # Binary / build outputs
    "bin",
    "x64",
    "x86",
    "win32",
    "win64",
    "amd64",
    "arm64",
    "debug",
    "release",
    "build",
    "dist",
    "out",
    "output",
    # Code layout
    "src",
    "source",
    "sources",
    "lib",
    "libs",
    "library",
    "include",
    "includes",
    "headers",
    "obj",
    # Data / resources
    "data",
    "assets",
    "asset",
    "res",
    "resources",
    "resource",
    "content",
    "media",
    "config",
    "cfg",
    "settings",
    "conf",
    # Game internals
    "scripts",
    "script",
    "mods",
    "mod",
    "addons",
    "addon",
    "plugins",
    "plugin",
    "dlc",
    "patch",
    "patches",
    "maps",
    "levels",
    "world",
    "worlds",
    "textures",
    "texture",
    "shaders",
    "shader",
    "audio",
    "sound",
    "sounds",
    "music",
    "sfx",
    "video",
    "videos",
    "cutscenes",
    "movies",
    "ui",
    "hud",
    "gui",
    "fonts",
    "font",
    "icons",
    "saves",
    "save",
    "savegames",
    "savegame",
    "logs",
    "log",
    "temp",
    "tmp",
    "cache",
    # Language dirs
    "en",
    "en-us",
    "de",
    "fr",
    "es",
    "ru",
    "zh",
    "ja",
    "pt",
    "localization",
    "locales",
    "locale",
    "lang",
    "language",
    # Steam / Epic / GOG internal layout
    "steamapps",
    "common",
    "workshop",
    "epic games",
    "gog games",
    "gog galaxy",
    "steamlibrary",
    "steam library",
    # Game/software library containers (hold many independent groups)
    "games",
    "game",
    "program files",
    "program files (x86)",
    "downloads",
    # Additional game-internal asset folders
    "meshes",
    "mesh",
    "animations",
    "animation",
    "characters",
    "character",
    "effects",
    "effect",
    "particles",
    "particle",
    "environments",
    "environment",
    # Generic catch-alls
    "misc",
    "other",
    "extras",
    "backup",
    "old",
    "new",
    "docs",
    "doc",
    "documentation",
    "help",
    "examples",
    "example",
    "samples",
    "sample",
    "test",
    "tests",
}

_MIN_FILES_FOR_GROUP = 2


# ── Public API ────────────────────────────────────────────────────────────────


def detect_groups(root: str) -> list[dict]:
    """
    Deep-scan *root* and return one group descriptor per logical unit found.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return []

    # Step 1 — collect all leaf dirs and their extensions
    leaf_data: dict[str, set[str]] = {}  # path_str → set of extensions
    _collect_leaves(root_path, root_path, leaf_data)

    if not leaf_data:
        return []

    # Step 1b — find every folder that directly contains a .exe (game/app anchor),
    # then propagate each anchor UP to its logical game/app root
    # (e.g. GAME\bin\game.exe → GAME, not bin)
    exe_anchors: frozenset[str] = frozenset(
        leaf_str for leaf_str, exts in leaf_data.items() if ".exe" in exts
    )
    game_roots: frozenset[str] = frozenset(
        str(_game_root_from_anchor(Path(a), root_path)) for a in exe_anchors
    )

    # Step 2 — bubble up each leaf to its group root; merge extensions
    group_exts: dict[str, set[str]] = {}  # group_root_str → all extensions
    for leaf_str, exts in leaf_data.items():
        group_root = _find_group_root(Path(leaf_str), root_path, game_roots)
        key = str(group_root)
        if key not in group_exts:
            group_exts[key] = set()
        group_exts[key].update(exts)

    # Step 3 — build descriptors
    groups = []
    for root_str, exts in group_exts.items():
        grp_path = Path(root_str)
        file_count = _count_files_recursive(grp_path)
        if file_count < _MIN_FILES_FOR_GROUP:
            continue
        total_size = _sum_size_recursive(grp_path)
        category = categorize_folder(grp_path, list(exts))
        groups.append(
            {
                "name": grp_path.name,
                "root_path": root_str,
                "category": category,
                "file_count": file_count,
                "total_size": total_size,
                "extensions": sorted(exts),
                "description": _describe(grp_path.name, category, file_count),
            }
        )

    return groups


# ── Internal helpers ──────────────────────────────────────────────────────────


def _collect_leaves(
    path: Path,
    scan_root: Path,
    result: dict[str, set[str]],
    depth: int = 0,
    max_depth: int = 12,
) -> None:
    """Recursively populate *result* with leaf dirs → extension sets."""
    if depth > max_depth:
        return
    try:
        entries = list(path.iterdir())
    except PermissionError:
        return

    files = [e for e in entries if e.is_file()]
    subdirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]

    if files:
        exts = {f.suffix.lower() for f in files}
        result[str(path)] = exts

    for sub in subdirs:
        _collect_leaves(sub, scan_root, result, depth + 1, max_depth)


def _game_root_from_anchor(anchor: Path, scan_root: Path) -> Path:
    """
    Walk UP from *anchor* (a folder containing a .exe) to find the logical
    game/app root: the first non-generic ancestor at-or-above the anchor.
    Examples:
      <root>/Games/Minecraft          -> Minecraft  (anchor has .exe, not generic)
      <root>/Games/Minecraft/bin      -> Minecraft  (bin is generic -> go up)
      <root>/steamapps/common/Skyrim  -> Skyrim
    """
    current = anchor
    while current != scan_root and current != current.parent:
        if current.name.lower() not in _GENERIC:
            return current
        current = current.parent
    return anchor  # fallback: use anchor itself


def _find_group_root(
    leaf: Path,
    scan_root: Path,
    game_roots: frozenset[str] = frozenset(),
) -> Path:
    """
    Walk UP from *leaf* toward *scan_root* and decide which folder is the
    logical group root.

    Game-root rule (highest priority):
      If any ancestor of *leaf* is a known game root (derived from all .exe
      anchor folders propagated upward), return that ancestor immediately.
      This correctly handles both direct executables (GAME/game.exe) and
      executables in sub-directories (GAME/bin/game.exe).

    Fallback (no game root found in path):
      Return the highest non-generic ancestor below scan_root.
    """
    # Build ordered list of segments from leaf up to (but not including) scan_root
    segments: list[Path] = []
    current = leaf
    while current != scan_root and current != current.parent:
        segments.append(current)
        current = current.parent

    if not segments:
        return leaf

    # Check whether any segment IS a known game root — return it immediately
    for seg in segments:
        if str(seg) in game_roots:
            return seg

    # No game root in path — fall back to highest non-generic ancestor
    candidates = [s for s in segments if s.name.lower() not in _GENERIC]
    if not candidates:
        return leaf
    return min(candidates, key=lambda p: len(p.parts))


def _count_files_recursive(path: Path) -> int:
    count = 0
    try:
        for _, _, files in os.walk(path):
            count += len(files)
    except PermissionError:
        pass
    return count


def _sum_size_recursive(path: Path) -> int:
    total = 0
    try:
        for dirpath, _, files in os.walk(path):
            for f in files:
                with contextlib.suppress(OSError):
                    total += (Path(dirpath) / f).stat().st_size
    except PermissionError:
        pass
    return total


def _describe(name: str, category: str, file_count: int) -> str:
    templates = {
        "Games": f"Game installation '{name}' with {file_count} files.",
        "Movies": f"Movie collection '{name}' containing {file_count} video files.",
        "Music": f"Music album/collection '{name}' with {file_count} tracks.",
        "Documents": f"Document folder '{name}' with {file_count} files.",
        "Images": f"Image gallery '{name}' with {file_count} photos.",
        "Software": f"Software installation '{name}' with {file_count} files.",
        "Other": f"Folder '{name}' with {file_count} files.",
    }
    return templates.get(category, templates["Other"])


# ── DB-only re-grouping ───────────────────────────────────────────────────────


def regroup_from_db(db, root_path: str) -> list[dict]:
    """
    Same logic as detect_groups() but reads file metadata directly from the
    database instead of walking the disk.  Safe to call after recategorize.
    """
    import os

    from sqlalchemy import func

    from database.models import FileRecord

    root = Path(root_path)
    sep = os.sep
    # Strip trailing separator to avoid double-separator in LIKE pattern.
    # e.g. "C:\" + "\" + "%" would produce "C:\\%" (double backslash) which
    # never matches real paths like "C:\Users\...".  Stripping gives "C:\%".
    clean_root = root_path.rstrip(sep) or sep
    like_prefix = clean_root + sep + "%"

    # 1 — collect all (parent_dir, extension) for files under this root
    rows = (
        db.query(FileRecord.parent_dir, FileRecord.extension)
        .filter(
            (FileRecord.parent_dir == root_path)
            | (FileRecord.parent_dir == clean_root)
            | FileRecord.parent_dir.like(like_prefix)
        )
        .all()
    )
    if not rows:
        return []

    # Build leaf_data: parent_dir → set of extensions (mirrors _collect_leaves)
    leaf_data: dict[str, set[str]] = {}
    for parent_dir, ext in rows:
        if parent_dir not in leaf_data:
            leaf_data[parent_dir] = set()
        if ext:
            leaf_data[parent_dir].add(ext.lower())

    # 1b — exe-anchors: folders that directly contain a .exe (DB query)
    exe_anchor_rows = (
        db.query(FileRecord.parent_dir)
        .filter(
            FileRecord.extension == ".exe",
            (FileRecord.parent_dir == root_path)
            | (FileRecord.parent_dir == clean_root)
            | FileRecord.parent_dir.like(like_prefix),
        )
        .distinct()
        .all()
    )
    exe_anchors = frozenset(r[0] for r in exe_anchor_rows)

    # Propagate each exe-anchor up to its logical game/app root
    # (e.g. GAME\bin with game.exe -> GAME, not bin)
    game_roots: frozenset[str] = frozenset(
        str(_game_root_from_anchor(Path(a), root)) for a in exe_anchors
    )

    # 2 — bubble up each leaf to its group root
    group_exts: dict[str, set[str]] = {}
    for leaf_str, exts in leaf_data.items():
        grp_root = _find_group_root(Path(leaf_str), root, game_roots)
        key = str(grp_root)
        if key not in group_exts:
            group_exts[key] = set()
        group_exts[key].update(exts)

    # 3 — build descriptors using DB counts (no disk reads)
    groups = []
    for root_str, exts in group_exts.items():
        grp_path = Path(root_str)
        clean_root_str = root_str.rstrip(sep)
        count_like = clean_root_str + sep + "%"

        file_count = (
            db.query(func.count(FileRecord.id))
            .filter((FileRecord.parent_dir == root_str) | FileRecord.parent_dir.like(count_like))
            .scalar()
        ) or 0

        if file_count < _MIN_FILES_FOR_GROUP:
            continue

        total_size = (
            db.query(func.sum(FileRecord.size_bytes))
            .filter((FileRecord.parent_dir == root_str) | FileRecord.parent_dir.like(count_like))
            .scalar()
        ) or 0

        category = categorize_folder(grp_path, list(exts))
        groups.append(
            {
                "name": grp_path.name,
                "root_path": root_str,
                "category": category,
                "file_count": file_count,
                "total_size": total_size,
                "extensions": sorted(exts),
                "description": _describe(grp_path.name, category, file_count),
            }
        )

    return groups
