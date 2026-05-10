"""
AI-based file categorization module.

Strategy (in priority order):
  1. Rule-based heuristics (fast, no external deps)
  2. scikit-learn TF-IDF classifier (trained on sample data, local)
  3. OpenAI API fallback (optional, if OPENAI_API_KEY is set)

The module exposes a single `categorize(file_path)` function.
"""

from __future__ import annotations

import re
from pathlib import Path

from config import (
    AI_BASE_URL,
    AI_MODEL,
    AUDIO_EXTENSIONS,
    DOC_EXTENSIONS,
    IMAGE_EXTENSIONS,
    OPENAI_API_KEY,
    VIDEO_EXTENSIONS,
    logger,
)

# ── Category constants ────────────────────────────────────────────────────────

CATEGORIES = ["Games", "Movies", "Documents", "Music", "Images", "Software", "Other"]

# ── Rule-based heuristics ─────────────────────────────────────────────────────

# Keywords that strongly suggest a category when found in directory name or file name
_KEYWORD_MAP: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"\bgame[s]?\b|\bsteam\b|\bepic\b|\bgog\b|\bmod[s]?\b|\bsave[s]?\b", re.I),
        "Games",
    ),
    (
        re.compile(
            r"\bmovie[s]?\b|\bfilm[s]?\b|\bcinema\b|\bseries\b|\bseason\b|\bepis\b|\bsubs?\b", re.I
        ),
        "Movies",
    ),
    (
        re.compile(r"\bmusic\b|\balbum\b|\bartist\b|\btrack[s]?\b|\bplaylist\b|\bsongs?\b", re.I),
        "Music",
    ),
    (
        re.compile(
            r"\bdoc[s]?\b|\bdocument[s]?\b|\breport[s]?\b|\binvoice\b|\bcontract\b|\bresume\b|\bcv\b",
            re.I,
        ),
        "Documents",
    ),
    (
        re.compile(
            r"\bphoto[s]?\b|\bpicture[s]?\b|\bimage[s]?\b|\bwallpaper[s]?\b|\bscreenshot[s]?\b",
            re.I,
        ),
        "Images",
    ),
    (
        re.compile(
            r"\bsetup\b|\binstaller\b|\bportable\b|\bsoftware\b|\bapp[s]?\b|\bprogram\b", re.I
        ),
        "Software",
    ),
]

_EXT_TO_CATEGORY: dict[str, str] = {}
for ext in VIDEO_EXTENSIONS:
    _EXT_TO_CATEGORY[ext] = "Movies"
for ext in AUDIO_EXTENSIONS:
    _EXT_TO_CATEGORY[ext] = "Music"
for ext in IMAGE_EXTENSIONS:
    _EXT_TO_CATEGORY[ext] = "Images"
for ext in DOC_EXTENSIONS:
    _EXT_TO_CATEGORY[ext] = "Documents"
# Executables/installers alone are "Software", not "Games".
# Games are identified at the folder/group level by _is_game_folder().
_EXT_TO_CATEGORY[".exe"] = "Software"
_EXT_TO_CATEGORY[".msi"] = "Software"
_EXT_TO_CATEGORY[".lnk"] = "Other"
_EXT_TO_CATEGORY[".iso"] = "Other"  # ambiguous — resolved at folder level


def _rule_based(path: Path) -> str:
    """Return category using fast rule-based heuristics."""
    # 1. Check extension
    ext = path.suffix.lower()
    if ext in _EXT_TO_CATEGORY:
        return _EXT_TO_CATEGORY[ext]

    # 2. Check file name and parent directories for keywords
    search_text = " ".join(path.parts[-4:])  # last 4 path components
    for pattern, category in _KEYWORD_MAP:
        if pattern.search(search_text):
            return category

    return "Other"


# ── Sklearn classifier (optional lightweight ML) ──────────────────────────────

_clf = None  # lazy-loaded


def _build_classifier():
    """
    Build and return a TF-IDF + Logistic Regression classifier trained on
    synthetic examples.  This runs entirely locally with no internet access.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
    except ImportError:
        return None

    # Minimal training corpus: (text, label)
    training = [
        # Games
        ("game steam epic gog mod save level boss shooter rpg", "Games"),
        ("game exe iso bin rom emulator patch crack level", "Games"),
        ("steam library game saves achievements workshop", "Games"),
        # Movies
        ("movie film cinema season episode subtitle mkv mp4 avi", "Movies"),
        ("movie bluray hdrip dvdrip 1080p 720p trailer", "Movies"),
        ("series season episode subtitle srt", "Movies"),
        # Music
        ("music album artist track playlist song flac mp3 wav", "Music"),
        ("artist album year lyrics genre band concert", "Music"),
        # Documents
        ("document report invoice contract agreement pdf docx", "Documents"),
        ("resume cv letter memo spreadsheet excel powerpoint", "Documents"),
        # Images
        ("photo picture image wallpaper screenshot jpg png", "Images"),
        ("photo album vacation portrait selfie raw", "Images"),
        # Software
        ("setup installer portable software app program exe msi", "Software"),
        ("utility tool driver update patch release", "Software"),
        # Other
        ("backup temp log cache misc unknown", "Other"),
        ("data file archive zip rar 7z", "Other"),
    ]

    texts, labels = zip(*training, strict=False)
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(texts, labels)
    return pipeline


def _ml_categorize(path: Path) -> str | None:
    """Use the sklearn classifier as a secondary signal."""
    global _clf
    if _clf is None:
        _clf = _build_classifier()
    if _clf is None:
        return None

    text = " ".join(path.parts[-5:]).lower()
    try:
        return _clf.predict([text])[0]
    except Exception:
        return None


# ── OpenAI fallback ───────────────────────────────────────────────────────────


def _openai_categorize(path: Path) -> str | None:
    """
    Categorize using an OpenAI-compatible chat API.

    Supports three modes (controlled by env vars):
      1. OpenAI cloud  — set OPENAI_API_KEY only
      2. Ollama local  — set AI_BASE_URL=http://localhost:11434/v1  AI_MODEL=llama3
      3. LM Studio     — set AI_BASE_URL=http://localhost:1234/v1   AI_MODEL=local-model

    openai package is optional; skipped silently if not installed.
    """
    # Need either an API key (cloud) or a local base URL
    if not OPENAI_API_KEY and not AI_BASE_URL:
        return None
    try:
        import openai  # type: ignore
    except ImportError:
        return None  # optional dependency not installed
    try:
        client = openai.OpenAI(
            api_key=OPENAI_API_KEY or "ollama",  # Ollama/LM Studio accept any value
            base_url=AI_BASE_URL or None,  # None = default OpenAI cloud URL
        )
        prompt = (
            f"Classify the following file path into exactly ONE of these categories: "
            f"{', '.join(CATEGORIES)}.\n\nPath: {path}\n\nReply with only the category name."
        )
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
        )
        result = response.choices[0].message.content.strip()
        if result in CATEGORIES:
            return result
    except Exception as exc:
        logger.warning("AI categorization failed: %s", exc)
    return None


# ── Public API ────────────────────────────────────────────────────────────────


def categorize(file_path: str | Path) -> str:
    """
    Return the best-guess category for a given file path.

    Priority: rule-based → ML → OpenAI → "Other"
    """
    path = Path(file_path)

    # Fast rule-based
    category = _rule_based(path)
    if category != "Other":
        return category

    # ML model (requires scikit-learn)
    ml_cat = _ml_categorize(path)
    if ml_cat and ml_cat != "Other":
        return ml_cat

    # OpenAI (optional)
    ai_cat = _openai_categorize(path)
    if ai_cat:
        return ai_cat

    return "Other"


# ── Game-folder asset extensions ─────────────────────────────────────────────
# Files commonly found inside a game installation (alongside an .exe)
_GAME_ASSET_EXTENSIONS = {
    ".pak",
    ".vpk",
    ".bsp",
    ".wad",
    ".gcf",
    ".ncf",  # game data packs
    ".dll",  # shared libs (also in games)
    ".cfg",
    ".ini",
    ".conf",  # config files
    ".sav",
    ".save",  # save files
    ".dat",
    ".db",  # data files
    ".nif",
    ".dds",
    ".tga",  # 3D/texture formats
    ".ogg",
    ".wav",  # audio in games
    ".bik",
    ".bk2",  # game video cutscenes
    ".esm",
    ".esp",
    ".esl",  # Bethesda plugin formats
    ".xnb",  # XNA/MonoGame content
    ".unity3d",
    ".assets",  # Unity game bundles
    ".uasset",
    ".umap",  # Unreal Engine assets
}

# Keywords in the folder NAME that strongly indicate a game install
_GAME_FOLDER_PATTERNS = re.compile(
    r"\bsteam\b|steamapps|\bgog\b|\bepic\b|\bgames?\b|\bplay\b"
    r"|\blevel\b|\bworld\b|\bdungeon\b|\bquest\b|\bcraft\b"
    r"|\bskyrim\b|\bfallout\b|\bwitcher\b|\bminecraft\b"
    r"|\bdiablo\b|\bdoom\b|\bquake\b|\bcs2?\b|\bdota\b",
    re.I,
)

# Keywords that mean it's an installer / software, NOT a game
_INSTALLER_PATTERNS = re.compile(
    r"\bsetup\b|\binstall\b|\buninstall\b|\bportable\b"
    r"|\badoble\b|\boffice\b|\bvisual.?studio\b|\bchrome\b"
    r"|\bfirefox\b|\bvlc\b|\bwinrar\b|\b7\-?zip\b",
    re.I,
)


def _is_game_folder(folder_path: Path, ext_set: set[str]) -> bool:
    """
    Return True if this folder looks like a game installation.
    Heuristic: has an .exe AND a significant number of game-asset extensions,
    OR the folder path contains strong game-related keywords.
    """
    folder_text = " ".join(folder_path.parts[-6:])

    # Explicitly software-named folders are never games
    if _INSTALLER_PATTERNS.search(folder_text):
        return False

    has_exe = ".exe" in ext_set
    has_iso = ".iso" in ext_set
    game_assets = ext_set & _GAME_ASSET_EXTENSIONS

    # Strong keyword signal in path → Game
    if _GAME_FOLDER_PATTERNS.search(folder_text) and (has_exe or has_iso):
        return True

    # Exe + multiple game-asset types → very likely a game
    if has_exe and len(game_assets) >= 2:
        return True

    # ISO/disc image without video files → likely a game disc
    return bool(has_iso and not ext_set & VIDEO_EXTENSIONS)


def categorize_folder(folder_path: str | Path, file_extensions: list[str]) -> str:
    """
    Determine the category of an entire folder based on its contents.
    Used for group detection — called with the NAMED group root, not a
    generic sub-folder like 'bin' or 'data'.
    """
    path = Path(folder_path)
    ext_set = {e.lower() for e in file_extensions}

    # ── Game detection (must come before generic ext lookup) ──────────────────
    if _is_game_folder(path, ext_set):
        return "Games"

    # ── Count votes from extension mapping ───────────────────────────────────
    counts: dict[str, int] = {}
    for ext in ext_set:
        cat = _EXT_TO_CATEGORY.get(ext, "Other")
        counts[cat] = counts.get(cat, 0) + 1

    # Folder-name keyword override
    folder_text = " ".join(path.parts[-4:])
    for pattern, category in _KEYWORD_MAP:
        if pattern.search(folder_text):
            return category

    if not counts:
        return "Other"

    return max(counts, key=counts.get)
