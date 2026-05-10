"""
DLL Deduplication Service.

Finds identical DLL files across game groups (by SHA-256 hash) and replaces
duplicate copies with hard-links (same drive) or symlinks (cross-drive) that
all point to a single canonical copy stored in a shared directory.

Extract-All mode moves EVERY DLL from selected game groups into the shared
directory (not just duplicates), stores a compressed zip backup alongside each
canonical file, maintains a shared index.json for fast name+hash lookup, and
writes a per-group manifest JSON so the exact set of extracted DLLs is
always known without opening any archive.

All heavy work runs in daemon threads; progress is tracked in-memory keyed by
job_id (a UUID string returned to the caller).
"""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import os
import shutil
import threading
import uuid
import zipfile
from pathlib import Path

from backend.config import logger
from database.models import DedupEntry, DedupLink, FileGroup, SessionLocal

# ── Constants ─────────────────────────────────────────────────────────────────

# Extensions treated as "shared libraries" for deduplication
DLL_EXTENSIONS = {".dll", ".so", ".dylib"}

# ── In-memory job registry ────────────────────────────────────────────────────

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _set_job(job_id: str, data: dict) -> None:
    with _lock:
        _jobs[job_id] = data


def get_job(job_id: str) -> dict:
    with _lock:
        return dict(_jobs.get(job_id, {"status": "not_found", "progress": 0}))


def new_job_id() -> str:
    return str(uuid.uuid4())


# ── File helpers ──────────────────────────────────────────────────────────────


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Return the SHA-256 hex digest of *path*. Reads in 1 MB chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _same_device(path_a: Path, path_b: Path) -> bool:
    """Return True if both paths reside on the same filesystem device."""
    try:
        return path_a.stat().st_dev == path_b.stat().st_dev
    except OSError:
        return False


def _can_hardlink(src: Path, dst_dir: Path) -> bool:
    """Check whether *src* and *dst_dir* are on the same device (hardlink requires this)."""
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        return _same_device(src, dst_dir)
    except OSError:
        return False


def _collect_dlls(groups: list) -> list[dict]:
    """Walk each group's root_path and return a flat list of DLL file info dicts."""
    result: list[dict] = []
    for grp in groups:
        if grp.is_archived:
            continue
        root = Path(grp.root_path)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in DLL_EXTENSIONS:
                with contextlib.suppress(OSError):
                    result.append(
                        {
                            "path": p,
                            "size": p.stat().st_size,
                            "group_id": grp.id,
                            "group_name": grp.name,
                        }
                    )
    return result


# ── Public: start jobs ────────────────────────────────────────────────────────


def start_analyze(group_ids: list[int] | None = None) -> str:
    """Scan game groups for duplicate DLLs (read-only / dry-run). Returns job_id."""
    job_id = new_job_id()
    _set_job(
        job_id,
        {"status": "running", "phase": "scanning", "progress": 0, "result": None, "error": None},
    )
    t = threading.Thread(
        target=_analyze_worker,
        args=(job_id, group_ids),
        daemon=True,
        name=f"dedup-analyze-{job_id[:8]}",
    )
    t.start()
    return job_id


def start_apply(shared_dir: str, group_ids: list[int] | None = None) -> str:
    """Create hard/symlinks to eliminate duplicate DLLs. Returns job_id."""
    job_id = new_job_id()
    _set_job(
        job_id,
        {"status": "running", "phase": "hashing", "progress": 0, "result": None, "error": None},
    )
    t = threading.Thread(
        target=_apply_worker,
        args=(job_id, shared_dir, group_ids),
        daemon=True,
        name=f"dedup-apply-{job_id[:8]}",
    )
    t.start()
    return job_id


def start_restore(group_ids: list[int] | None = None) -> str:
    """Replace all tracked links with real file copies. Returns job_id."""
    job_id = new_job_id()
    _set_job(
        job_id,
        {"status": "running", "phase": "restoring", "progress": 0, "result": None, "error": None},
    )
    t = threading.Thread(
        target=_restore_worker,
        args=(job_id, group_ids),
        daemon=True,
        name=f"dedup-restore-{job_id[:8]}",
    )
    t.start()
    return job_id


def start_extract_all(shared_dir: str, group_ids: list[int] | None = None) -> str:
    """Extract ALL DLLs from selected groups into shared storage.

    For every DLL found:
    - Canonical copy stored at  shared_dir/{hash12}_{name}
    - Compressed backup stored at shared_dir/{hash12}_{name}.zip
    - Original replaced with a hardlink (or symlink) to the canonical copy
    - shared_dir/index.json updated with name + hash for fast lookup
    - shared_dir/manifests/{group_id}.json created/updated per group
    Returns job_id.
    """
    job_id = new_job_id()
    _set_job(
        job_id,
        {"status": "running", "phase": "scanning", "progress": 0, "result": None, "error": None},
    )
    t = threading.Thread(
        target=_extract_all_worker,
        args=(job_id, shared_dir, group_ids),
        daemon=True,
        name=f"dedup-extract-{job_id[:8]}",
    )
    t.start()
    return job_id


# ── Shared-directory index helpers ────────────────────────────────────────────

_INDEX_FILE = "index.json"
_MANIFESTS_DIR = "manifests"
_index_lock = threading.Lock()


def _load_index(shared_path: Path) -> dict:
    """Load shared/index.json; returns dict keyed by sha256."""
    idx_file = shared_path / _INDEX_FILE
    if idx_file.exists():
        try:
            with idx_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("dlls", {})
        except Exception:
            pass
    return {}


def _save_index(shared_path: Path, dlls: dict) -> None:
    """Atomically write shared/index.json."""
    idx_file = shared_path / _INDEX_FILE
    tmp = idx_file.with_suffix(".json.tmp")
    payload = {
        "version": 1,
        "updated_at": datetime.datetime.utcnow().isoformat(),
        "dlls": dlls,
    }
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(idx_file)


def _save_group_manifest(
    shared_path: Path, group_id: int, group_name: str, entries: list[dict]
) -> str:
    """Write shared/manifests/{group_id}.json; returns path string."""
    manifests_dir = shared_path / _MANIFESTS_DIR
    manifests_dir.mkdir(exist_ok=True)
    manifest_file = manifests_dir / f"{group_id}.json"
    tmp = manifest_file.with_suffix(".json.tmp")
    payload = {
        "group_id": group_id,
        "group_name": group_name,
        "extracted_at": datetime.datetime.utcnow().isoformat(),
        "dlls": entries,
    }
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(manifest_file)
    return str(manifest_file)


def extract_dlls_inline(
    group_id: int,
    grp_name: str,
    root_path: Path,
    shared_dir: str,
    db,
    progress_callback=None,  # Optional[Callable[[int], None]]  0-100 sub-range
) -> list[dict]:
    """Extract DLLs to shared storage only when they are ALSO present in another active game.

    DLLs unique to this game are left alone — they will be included in the game zip as
    normal files. Only truly shared DLLs go to shared storage.

    Returns a list of manifest entry dicts for DLLs that were saved to shared storage.
    The caller uses this list to:
      1. Embed it as _dlls.json inside the game zip (for restore).
      2. Exclude those specific files from the game zip (they live in shared storage).
    """
    shared_path = Path(shared_dir)
    shared_path.mkdir(parents=True, exist_ok=True)

    # Collect DLLs in this group
    dll_files: list[dict] = []
    for p in root_path.rglob("*"):
        if p.is_file() and p.suffix.lower() in DLL_EXTENSIONS:
            with contextlib.suppress(OSError):
                dll_files.append({"path": p, "size": p.stat().st_size})

    if not dll_files:
        return []

    # Hash DLLs in every OTHER non-archived group to identify truly shared DLLs
    other_groups = (
        db.query(FileGroup)
        .filter(
            FileGroup.id != group_id,
            FileGroup.is_archived.is_(False),
        )
        .all()
    )
    other_hashes: set[str] = set()
    total_other = len(other_groups)
    for gi, grp in enumerate(other_groups):
        if progress_callback:
            # Report 0-50% for scanning other groups
            progress_callback(int((gi / max(total_other, 1)) * 50))
        if not grp.root_path:
            continue
        other_root = Path(grp.root_path)
        if not other_root.exists():
            continue
        for p in other_root.rglob("*"):
            if p.is_file() and p.suffix.lower() in DLL_EXTENSIONS:
                with contextlib.suppress(OSError):
                    other_hashes.add(sha256_file(p))
    if progress_callback:
        progress_callback(50)

    with _index_lock:
        index = _load_index(shared_path)

    manifest_entries: list[dict] = []
    extracted = 0
    skipped_unique = 0

    for f in dll_files:
        orig_path: Path = f["path"]
        dll_name = orig_path.name
        try:
            h = sha256_file(orig_path)
        except OSError:
            continue

        # Not shared with any other active game → stays in game zip, not in shared storage
        if h not in other_hashes:
            skipped_unique += 1
            continue

        zip_name = f"{h[:12]}_{dll_name}.zip"
        archive_path = shared_path / zip_name

        try:
            with db.begin_nested():
                # Already stored and zip exists → just record in manifest
                if h in index and Path(index[h]["archive_path"]).exists():
                    manifest_entries.append(
                        {
                            "original_path": str(orig_path),
                            "sha256": h,
                            "name": dll_name,
                            "size_bytes": f["size"],
                            "archive_path": str(index[h]["archive_path"]),
                            "link_type": "already_stored",
                        }
                    )
                    continue

                # Create zip from the original file
                if not archive_path.exists():
                    with zipfile.ZipFile(
                        str(archive_path), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
                    ) as zf:
                        zf.write(str(orig_path), dll_name)

                # Upsert DedupEntry
                entry = db.query(DedupEntry).filter(DedupEntry.sha256 == h).first()
                if not entry:
                    entry = DedupEntry(
                        sha256=h,
                        shared_path=str(archive_path),
                        dll_name=dll_name,
                        size_bytes=float(f["size"]),
                        link_count=0,
                        created_at=datetime.datetime.utcnow(),
                    )
                    db.add(entry)
                    db.flush()

                # Upsert DedupLink
                existing_link = (
                    db.query(DedupLink).filter(DedupLink.linked_path == str(orig_path)).first()
                )
                if existing_link:
                    existing_link.link_type = "archive_copy"
                else:
                    db.add(
                        DedupLink(
                            dedup_entry_id=entry.id,
                            linked_path=str(orig_path),
                            group_id=group_id,
                            link_type="archive_copy",
                            created_at=datetime.datetime.utcnow(),
                        )
                    )
                    entry.link_count = (entry.link_count or 0) + 1

                index[h] = {
                    "name": dll_name,
                    "sha256": h,
                    "size_bytes": f["size"],
                    "archive_path": str(archive_path),
                }
                extracted += 1
                manifest_entries.append(
                    {
                        "original_path": str(orig_path),
                        "sha256": h,
                        "name": dll_name,
                        "size_bytes": f["size"],
                        "archive_path": str(archive_path),
                        "link_type": "archive_copy",
                    }
                )

        except Exception as exc:
            logger.warning("DLL extract (archive) failed for %s: %s", orig_path, exc)

    db.commit()

    with _index_lock:
        _save_index(shared_path, index)

    logger.info(
        "DLL extract (archive) group %d: %d shared → shared storage, %d unique → game zip",
        group_id,
        extracted,
        skipped_unique,
    )
    return manifest_entries


def cleanup_orphaned_shared_dlls(group_id: int, shared_dir: str, db) -> int:
    """Remove shared DLL zips that no active (non-archived) game needs anymore.

    Called after a group is archived and committed to DB. Any DedupEntry whose
    only remaining DedupLinks point to archived groups is deleted along with its zip.
    Returns the number of DLL zips removed.
    """
    shared_path = Path(shared_dir)

    # All entries this group contributed
    links_for_group = db.query(DedupLink).filter(DedupLink.group_id == group_id).all()
    if not links_for_group:
        return 0

    entry_ids = {lnk.dedup_entry_id for lnk in links_for_group}
    removed = 0

    with _index_lock:
        index = _load_index(shared_path)

        for entry_id in entry_ids:
            # Count links from OTHER non-archived groups
            active_other = (
                db.query(DedupLink)
                .join(FileGroup, DedupLink.group_id == FileGroup.id)
                .filter(
                    DedupLink.dedup_entry_id == entry_id,
                    DedupLink.group_id != group_id,
                    FileGroup.is_archived.is_(False),
                )
                .count()
            )
            if active_other > 0:
                continue  # still needed by an active game

            entry = db.get(DedupEntry, entry_id)
            if not entry:
                continue

            # No active game needs this DLL → delete zip and DB records
            with contextlib.suppress(OSError):
                Path(entry.shared_path).unlink()

            index.pop(entry.sha256, None)
            db.query(DedupLink).filter(DedupLink.dedup_entry_id == entry_id).delete()
            db.delete(entry)
            removed += 1

        if removed:
            _save_index(shared_path, index)

    if removed:
        db.commit()
        logger.info("Removed %d orphaned shared DLL(s) after archiving group %d", removed, group_id)
    return removed


# ── Workers ───────────────────────────────────────────────────────────────────


def _extract_all_worker(job_id: str, shared_dir: str, group_ids: list[int] | None) -> None:
    """Move ALL DLLs from selected groups into shared storage with zip backups."""
    db = SessionLocal()
    try:
        shared_path = Path(shared_dir)
        shared_path.mkdir(parents=True, exist_ok=True)

        groups = db.query(FileGroup)
        if group_ids:
            groups = groups.filter(FileGroup.id.in_(group_ids))
        groups = groups.all()

        dll_files = _collect_dlls(groups)
        total = len(dll_files)

        if not total:
            _set_job(
                job_id,
                {
                    "status": "done",
                    "progress": 100,
                    "phase": "done",
                    "result": {"extracted": 0, "skipped": 0, "saved_bytes": 0, "errors": []},
                    "error": None,
                },
            )
            return

        _set_job(
            job_id,
            {"status": "running", "phase": "hashing", "progress": 2, "result": None, "error": None},
        )

        # Hash all DLLs
        hashed: list[dict] = []
        for i, f in enumerate(dll_files):
            try:
                h = sha256_file(f["path"])
                hashed.append({**f, "hash": h})
            except OSError:
                pass
            if i % 20 == 0:
                pct = 2 + int((i + 1) / total * 48)
                _set_job(
                    job_id,
                    {
                        "status": "running",
                        "phase": "hashing",
                        "progress": pct,
                        "result": None,
                        "error": None,
                    },
                )

        _set_job(
            job_id,
            {
                "status": "running",
                "phase": "extracting",
                "progress": 52,
                "result": None,
                "error": None,
            },
        )

        # Load existing index (thread-safe)
        with _index_lock:
            index: dict = _load_index(shared_path)

        # Group by group_id for per-group manifests
        by_group: dict[int, list] = {}
        for f in hashed:
            by_group.setdefault(f["group_id"], []).append(f)

        extracted = 0
        skipped = 0
        saved_bytes = 0
        errors: list[str] = []
        done_ops = 0
        total_ops = len(hashed)

        for grp_id, dll_list in by_group.items():
            grp_obj = next((g for g in groups if g.id == grp_id), None)
            grp_name = grp_obj.name if grp_obj else str(grp_id)
            manifest_entries: list[dict] = []

            for f in dll_list:
                done_ops += 1
                pct = 52 + int(done_ops / max(total_ops, 1) * 44)
                if done_ops % 10 == 0:
                    _set_job(
                        job_id,
                        {
                            "status": "running",
                            "phase": "extracting",
                            "progress": pct,
                            "result": None,
                            "error": None,
                        },
                    )

                h: str = f["hash"]
                orig_path: Path = f["path"]
                dll_name: str = orig_path.name
                canonical_name = f"{h[:12]}_{dll_name}"
                canonical = shared_path / canonical_name
                archive_path = shared_path / f"{canonical_name}.zip"

                try:
                    # Skip if already linked (tracked in DB)
                    if db.query(DedupLink).filter(DedupLink.linked_path == str(orig_path)).first():
                        skipped += 1
                        manifest_entries.append(
                            {
                                "original_path": str(orig_path),
                                "sha256": h,
                                "name": dll_name,
                                "size_bytes": f["size"],
                                "shared_path": str(canonical),
                                "archive_path": str(archive_path),
                                "link_type": "already_linked",
                            }
                        )
                        continue

                    # Ensure canonical copy exists in shared dir
                    entry = db.query(DedupEntry).filter(DedupEntry.sha256 == h).first()
                    if entry:
                        canonical = Path(entry.shared_path)
                        archive_path = canonical.with_name(canonical.name + ".zip")
                        if not canonical.exists() and orig_path.exists():
                            shutil.copy2(str(orig_path), str(canonical))
                    else:
                        # Copy DLL to shared (if not already there)
                        if not canonical.exists() and orig_path.exists():
                            shutil.copy2(str(orig_path), str(canonical))
                        elif not canonical.exists():
                            errors.append(f"Source missing: {dll_name}")
                            continue

                        entry = DedupEntry(
                            sha256=h,
                            shared_path=str(canonical),
                            dll_name=dll_name,
                            size_bytes=float(f["size"]),
                            link_count=0,
                            created_at=datetime.datetime.utcnow(),
                        )
                        db.add(entry)
                        db.flush()

                    # Create zip archive if not already present
                    if not archive_path.exists() and canonical.exists():
                        with zipfile.ZipFile(
                            str(archive_path),
                            "w",
                            compression=zipfile.ZIP_DEFLATED,
                            compresslevel=6,
                        ) as zf:
                            zf.write(str(canonical), canonical.name)

                    # Update shared index
                    index[h] = {
                        "name": dll_name,
                        "sha256": h,
                        "size_bytes": f["size"],
                        "shared_path": str(canonical),
                        "archive_path": str(archive_path),
                    }

                    # Replace original with hardlink / symlink
                    if not orig_path.exists():
                        skipped += 1
                        continue

                    use_hardlink = _can_hardlink(canonical, orig_path.parent)
                    tmp = orig_path.with_name(orig_path.name + ".dedup_tmp")
                    tmp.unlink(missing_ok=True)

                    link_type: str
                    if use_hardlink:
                        os.link(str(canonical), str(tmp))
                        link_type = "hardlink"
                    else:
                        try:
                            os.symlink(str(canonical), str(tmp))
                            link_type = "symlink"
                        except OSError as sym_err:
                            errors.append(f"Symlink failed ({dll_name}): {sym_err}")
                            tmp.unlink(missing_ok=True)
                            skipped += 1
                            continue

                    orig_path.unlink()
                    tmp.rename(orig_path)

                    link_rec = DedupLink(
                        dedup_entry_id=entry.id,
                        linked_path=str(orig_path),
                        group_id=grp_id,
                        link_type=link_type,
                        created_at=datetime.datetime.utcnow(),
                    )
                    db.add(link_rec)
                    entry.link_count = (entry.link_count or 0) + 1
                    extracted += 1
                    saved_bytes += f["size"]

                    manifest_entries.append(
                        {
                            "original_path": str(orig_path),
                            "sha256": h,
                            "name": dll_name,
                            "size_bytes": f["size"],
                            "shared_path": str(canonical),
                            "archive_path": str(archive_path),
                            "link_type": link_type,
                        }
                    )

                except Exception as exc:
                    logger.warning("Extract failed %s: %s", orig_path, exc)
                    errors.append(f"Failed ({dll_name}): {exc}")
                    with contextlib.suppress(OSError):
                        orig_path.with_name(orig_path.name + ".dedup_tmp").unlink(missing_ok=True)

            # Write per-group manifest
            if manifest_entries:
                with contextlib.suppress(OSError):
                    _save_group_manifest(shared_path, grp_id, grp_name, manifest_entries)

        db.commit()

        # Persist updated index atomically
        with _index_lock:
            _save_index(shared_path, index)

        result = {
            "extracted": extracted,
            "skipped": skipped,
            "saved_bytes": saved_bytes,
            "errors": errors[:30],
            "index_path": str(shared_path / _INDEX_FILE),
        }
        _set_job(
            job_id,
            {"status": "done", "progress": 100, "phase": "done", "result": result, "error": None},
        )
        logger.info(
            "DLL extract-all: %d extracted, %d skipped, %.1f MB",
            extracted,
            skipped,
            saved_bytes / 1e6,
        )

    except Exception as exc:
        logger.exception("DLL extract-all failed (job %s)", job_id)
        db.rollback()
        _set_job(
            job_id,
            {"status": "error", "progress": 0, "phase": "error", "result": None, "error": str(exc)},
        )
    finally:
        db.close()


def _analyze_worker(job_id: str, group_ids: list[int] | None) -> None:
    db = SessionLocal()
    try:
        groups = db.query(FileGroup)
        if group_ids:
            groups = groups.filter(FileGroup.id.in_(group_ids))
        groups = groups.all()

        dll_files = _collect_dlls(groups)
        total = len(dll_files)

        if not total:
            _set_job(
                job_id,
                {
                    "status": "done",
                    "progress": 100,
                    "phase": "done",
                    "result": {
                        "total_dlls": 0,
                        "unique_dlls": 0,
                        "duplicate_groups": 0,
                        "potential_savings_bytes": 0,
                        "duplicates": [],
                    },
                    "error": None,
                },
            )
            return

        _set_job(
            job_id,
            {"status": "running", "phase": "hashing", "progress": 5, "result": None, "error": None},
        )

        # Hash every file
        hash_map: dict[str, list[dict]] = {}
        for i, f in enumerate(dll_files):
            try:
                h = sha256_file(f["path"])
                hash_map.setdefault(h, []).append({**f, "path": str(f["path"]), "hash": h})
            except OSError:
                pass
            pct = 5 + int((i + 1) / total * 85)
            if i % 20 == 0:
                _set_job(
                    job_id,
                    {
                        "status": "running",
                        "phase": "hashing",
                        "progress": pct,
                        "result": None,
                        "error": None,
                    },
                )

        # Find hashes with > 1 file
        duplicates = []
        potential_savings = 0
        for h, files in hash_map.items():
            if len(files) > 1:
                size = files[0]["size"]
                savings = (len(files) - 1) * size
                potential_savings += savings
                duplicates.append(
                    {
                        "hash": h,
                        "dll_name": Path(files[0]["path"]).name,
                        "size_bytes": size,
                        "count": len(files),
                        "savings_bytes": savings,
                        "files": [
                            {
                                "path": f["path"],
                                "group_id": f["group_id"],
                                "group_name": f["group_name"],
                            }
                            for f in files
                        ],
                    }
                )

        duplicates.sort(key=lambda d: d["savings_bytes"], reverse=True)

        result = {
            "total_dlls": total,
            "unique_dlls": len(hash_map),
            "duplicate_groups": len(duplicates),
            "potential_savings_bytes": potential_savings,
            "duplicates": duplicates[:300],  # cap for response size
        }

        _set_job(
            job_id,
            {"status": "done", "progress": 100, "phase": "done", "result": result, "error": None},
        )
        logger.info(
            "DLL analyze: %d files, %d dup groups, %.1f MB potential savings",
            total,
            len(duplicates),
            potential_savings / 1e6,
        )

    except Exception as exc:
        logger.exception("DLL analyze failed (job %s)", job_id)
        _set_job(
            job_id,
            {"status": "error", "progress": 0, "phase": "error", "result": None, "error": str(exc)},
        )
    finally:
        db.close()


def _apply_worker(job_id: str, shared_dir: str, group_ids: list[int] | None) -> None:
    db = SessionLocal()
    try:
        shared_path = Path(shared_dir)
        shared_path.mkdir(parents=True, exist_ok=True)

        groups = db.query(FileGroup)
        if group_ids:
            groups = groups.filter(FileGroup.id.in_(group_ids))
        groups = groups.all()

        dll_files = _collect_dlls(groups)
        total = len(dll_files)

        if not total:
            _set_job(
                job_id,
                {
                    "status": "done",
                    "progress": 100,
                    "phase": "done",
                    "result": {"linked": 0, "saved_bytes": 0, "errors": []},
                    "error": None,
                },
            )
            return

        _set_job(
            job_id,
            {"status": "running", "phase": "hashing", "progress": 2, "result": None, "error": None},
        )

        # Hash all files
        hash_map: dict[str, list[dict]] = {}
        for i, f in enumerate(dll_files):
            try:
                h = sha256_file(f["path"])
                hash_map.setdefault(h, []).append({**f, "hash": h})
            except OSError:
                pass
            pct = 2 + int((i + 1) / total * 58)
            if i % 20 == 0:
                _set_job(
                    job_id,
                    {
                        "status": "running",
                        "phase": "hashing",
                        "progress": pct,
                        "result": None,
                        "error": None,
                    },
                )

        _set_job(
            job_id,
            {
                "status": "running",
                "phase": "linking",
                "progress": 62,
                "result": None,
                "error": None,
            },
        )

        # Only process hashes with actual duplicates
        dup_groups = {h: files for h, files in hash_map.items() if len(files) > 1}
        total_ops = sum(len(v) for v in dup_groups.values())
        done_ops = 0
        linked_count = 0
        saved_bytes = 0
        errors: list[str] = []

        for h, files in dup_groups.items():
            size = files[0]["size"]
            dll_name = files[0]["path"].name

            # Look up or create the canonical entry
            entry = db.query(DedupEntry).filter(DedupEntry.sha256 == h).first()

            if entry:
                canonical = Path(entry.shared_path)
                # Rebuild canonical from any available source if it was lost
                if not canonical.exists():
                    src = next((f for f in files if f["path"].exists()), None)
                    if not src:
                        done_ops += len(files)
                        continue
                    shutil.copy2(str(src["path"]), str(canonical))
            else:
                # Create canonical: copy first available file into shared storage
                src = next((f for f in files if f["path"].exists()), None)
                if not src:
                    done_ops += len(files)
                    continue

                # Name = hash_prefix + original filename (avoids collisions)
                canonical_name = f"{h[:12]}_{dll_name}"
                canonical = shared_path / canonical_name
                shutil.copy2(str(src["path"]), str(canonical))

                entry = DedupEntry(
                    sha256=h,
                    shared_path=str(canonical),
                    dll_name=dll_name,
                    size_bytes=float(size),
                    link_count=0,
                    created_at=datetime.datetime.utcnow(),
                )
                db.add(entry)
                db.flush()  # get entry.id

            # Replace each duplicate with a link to canonical
            for f in files:
                orig_path: Path = f["path"]
                done_ops += 1
                pct = 62 + int(done_ops / max(total_ops, 1) * 36)
                _set_job(
                    job_id,
                    {
                        "status": "running",
                        "phase": "linking",
                        "progress": pct,
                        "result": None,
                        "error": None,
                    },
                )

                try:
                    # Skip if already tracked
                    if db.query(DedupLink).filter(DedupLink.linked_path == str(orig_path)).first():
                        continue
                    if not orig_path.exists():
                        continue
                    if not canonical.exists():
                        continue

                    # Decide link type
                    use_hardlink = _can_hardlink(canonical, orig_path.parent)

                    # Create the link in a temp location, then atomically swap
                    tmp = orig_path.with_name(orig_path.name + ".dedup_tmp")
                    tmp.unlink(missing_ok=True)

                    if use_hardlink:
                        os.link(str(canonical), str(tmp))
                        link_type = "hardlink"
                    else:
                        try:
                            os.symlink(str(canonical), str(tmp))
                            link_type = "symlink"
                        except OSError as sym_err:
                            errors.append(f"Symlink failed ({orig_path.name}): {sym_err}")
                            tmp.unlink(missing_ok=True)
                            continue

                    # Atomically swap: delete original then rename tmp
                    orig_path.unlink()
                    tmp.rename(orig_path)

                    # Record in DB
                    link_rec = DedupLink(
                        dedup_entry_id=entry.id,
                        linked_path=str(orig_path),
                        group_id=f["group_id"],
                        link_type=link_type,
                        created_at=datetime.datetime.utcnow(),
                    )
                    db.add(link_rec)
                    entry.link_count = (entry.link_count or 0) + 1
                    linked_count += 1
                    # Net savings: (copies - 1) × size; we count per-link but subtract
                    # the canonical overhead once per group (handled below)
                    saved_bytes += size

                except Exception as link_err:
                    logger.warning("Link failed %s: %s", orig_path, link_err)
                    errors.append(f"Link failed ({orig_path.name}): {link_err}")
                    tmp_p = orig_path.with_name(orig_path.name + ".dedup_tmp")
                    tmp_p.unlink(missing_ok=True)

            # Subtract one unit of size per dup group to account for the canonical copy
            if linked_count > 0:
                saved_bytes = max(0, saved_bytes - size)

        db.commit()

        result = {
            "linked": linked_count,
            "saved_bytes": saved_bytes,
            "errors": errors[:30],
        }
        _set_job(
            job_id,
            {"status": "done", "progress": 100, "phase": "done", "result": result, "error": None},
        )
        logger.info("DLL dedup apply: %d links, %.1f MB freed", linked_count, saved_bytes / 1e6)

    except Exception as exc:
        logger.exception("DLL dedup apply failed (job %s)", job_id)
        db.rollback()
        _set_job(
            job_id,
            {"status": "error", "progress": 0, "phase": "error", "result": None, "error": str(exc)},
        )
    finally:
        db.close()


def _restore_worker(job_id: str, group_ids: list[int] | None) -> None:
    db = SessionLocal()
    try:
        q = db.query(DedupLink)
        if group_ids:
            q = q.filter(DedupLink.group_id.in_(group_ids))
        links = q.all()

        total = len(links)
        restored = 0
        errors: list[str] = []

        for i, link in enumerate(links):
            pct = int((i + 1) / max(total, 1) * 94)
            _set_job(
                job_id,
                {
                    "status": "running",
                    "phase": "restoring",
                    "progress": pct,
                    "result": None,
                    "error": None,
                },
            )
            try:
                entry = db.get(DedupEntry, link.dedup_entry_id)
                if not entry:
                    db.delete(link)
                    continue

                canonical = Path(entry.shared_path)
                linked_path = Path(link.linked_path)

                if not canonical.exists():
                    errors.append(f"Canonical missing: {canonical.name}")
                    continue

                # Copy canonical → temp next to target, then swap
                tmp = linked_path.with_name(linked_path.name + ".restore_tmp")
                shutil.copy2(str(canonical), str(tmp))

                if linked_path.exists() or linked_path.is_symlink():
                    linked_path.unlink()
                tmp.rename(linked_path)

                entry.link_count = max(0, (entry.link_count or 1) - 1)
                db.delete(link)
                restored += 1

            except Exception as restore_err:
                logger.warning("Restore failed %s: %s", link.linked_path, restore_err)
                errors.append(f"Restore failed ({Path(link.linked_path).name}): {restore_err}")

        # Remove orphaned canonical files (entries with 0 links)
        orphans = db.query(DedupEntry).filter(DedupEntry.link_count <= 0).all()
        # Derive shared_path from the first orphan so we can update index.json
        shared_root: Path | None = Path(orphans[0].shared_path).parent if orphans else None
        orphan_hashes: set[str] = set()
        for entry in orphans:
            canonical = Path(entry.shared_path)
            with contextlib.suppress(OSError):
                canonical.unlink(missing_ok=True)
            # Also remove the zip backup if present
            zip_backup = canonical.with_name(canonical.name + ".zip")
            with contextlib.suppress(OSError):
                zip_backup.unlink(missing_ok=True)
            orphan_hashes.add(entry.sha256)
            db.delete(entry)

        db.commit()

        # Rebuild index.json to reflect removed entries
        if shared_root and shared_root.exists():
            with _index_lock:
                existing = _load_index(shared_root)
                cleaned = {h: v for h, v in existing.items() if h not in orphan_hashes}
                _save_index(shared_root, cleaned)

        result = {"restored": restored, "errors": errors[:30]}
        _set_job(
            job_id,
            {"status": "done", "progress": 100, "phase": "done", "result": result, "error": None},
        )
        logger.info("DLL dedup restore: %d files restored", restored)

    except Exception as exc:
        logger.exception("DLL dedup restore failed (job %s)", job_id)
        db.rollback()
        _set_job(
            job_id,
            {"status": "error", "progress": 0, "phase": "error", "result": None, "error": str(exc)},
        )
    finally:
        db.close()


# ── Stats ─────────────────────────────────────────────────────────────────────


def get_db_stats(db) -> dict:
    """Return current deduplication statistics from the database."""
    from sqlalchemy import func

    entry_count = db.query(func.count(DedupEntry.id)).scalar() or 0
    link_count = db.query(func.count(DedupLink.id)).scalar() or 0
    # saved = sum over all entries of (link_count × size_bytes)
    # because each link represents one copy we avoided
    saved_raw = db.query(func.sum(DedupEntry.size_bytes * DedupEntry.link_count)).scalar() or 0
    return {
        "unique_dlls_stored": entry_count,
        "total_links": link_count,
        "saved_bytes": float(saved_raw),
    }
