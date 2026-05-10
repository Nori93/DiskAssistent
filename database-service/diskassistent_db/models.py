"""
Database models and ORM layer using SQLAlchemy + SQLite.
Shared package used by both webapi and worker-service.
"""

from __future__ import annotations

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from diskassistent_db.config import DB_PATH, logger

# ── Engine & Session ──────────────────────────────────────────────────────────

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 60},
    poolclass=NullPool,
    echo=False,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=60000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency: yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Base ──────────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ── Models ────────────────────────────────────────────────────────────────────


class FileRecord(Base):
    """Represents a file discovered during scanning."""

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False, index=True)
    full_path = Column(Text, nullable=False, unique=True, index=True)
    parent_dir = Column(Text, nullable=False)
    extension = Column(String(32), index=True)
    size_bytes = Column(Float, default=0)
    created_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, nullable=True)
    scanned_at = Column(DateTime, default=datetime.datetime.utcnow)

    category = Column(String(64), default="Other", index=True)
    ai_category = Column(String(64), default="Other")
    category_overridden = Column(Boolean, default=False)
    tags = Column(Text, default="")
    description = Column(Text, default="")
    thumbnail_path = Column(Text, default="")
    group_id = Column(Integer, nullable=True, index=True)
    is_missing = Column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "full_path": self.full_path,
            "parent_dir": self.parent_dir,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "size_human": _human_size(self.size_bytes or 0),
            "created_at": _fmt_dt(self.created_at),
            "modified_at": _fmt_dt(self.modified_at),
            "scanned_at": _fmt_dt(self.scanned_at),
            "category": self.category,
            "ai_category": self.ai_category,
            "category_overridden": self.category_overridden,
            "tags": self.tags or "",
            "description": self.description or "",
            "thumbnail_path": self.thumbnail_path or "",
            "group_id": self.group_id,
            "is_missing": self.is_missing,
        }


class FileGroup(Base):
    """Represents a logical group of related files (e.g. a game folder)."""

    __tablename__ = "file_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False)
    root_path = Column(Text, nullable=False, unique=True)
    category = Column(String(64), default="Other", index=True)
    description = Column(Text, default="")
    thumbnail_path = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    file_tree_json = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    archive_path = Column(Text, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    archive_size_bytes = Column(Float, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "root_path": self.root_path,
            "category": self.category,
            "description": self.description,
            "thumbnail_path": self.thumbnail_path or "",
            "created_at": _fmt_dt(self.created_at),
            "is_archived": bool(self.is_archived),
            "archive_path": self.archive_path or "",
            "archived_at": _fmt_dt(self.archived_at),
            "archive_size_bytes": self.archive_size_bytes or 0,
            "archive_size_human": _human_size(self.archive_size_bytes or 0),
        }


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, index=True)
    root_path = Column(Text, nullable=False)
    status = Column(String(32), default="pending")
    total_files = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    error_msg = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    current_disk = Column(Text, default="")
    disk_progress = Column(Text, default="{}")

    def to_dict(self) -> dict:
        import json

        try:
            dp = json.loads(self.disk_progress or "{}")
        except Exception:
            dp = {}
        dur = None
        if self.started_at and self.finished_at:
            dur = round((self.finished_at - self.started_at).total_seconds(), 1)
        return {
            "id": self.id,
            "root_path": self.root_path,
            "status": self.status,
            "total_files": self.total_files,
            "processed": self.processed,
            "error_msg": self.error_msg,
            "started_at": _fmt_dt(self.started_at),
            "finished_at": _fmt_dt(self.finished_at),
            "progress_pct": (
                round(self.processed / self.total_files * 100, 1) if self.total_files else 0
            ),
            "duration_sec": dur,
            "current_disk": self.current_disk or "",
            "disk_progress": dp,
        }


class RecategorizeJob(Base):
    __tablename__ = "recategorize_jobs"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(Text, default="all")
    status = Column(String(32), default="pending")
    total = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    changed = Column(Integer, default=0)
    error_msg = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        dur = None
        if self.started_at and self.finished_at:
            dur = round((self.finished_at - self.started_at).total_seconds(), 1)
        return {
            "id": self.id,
            "scope": self.scope or "all",
            "status": self.status,
            "total": self.total,
            "processed": self.processed,
            "changed": self.changed,
            "error_msg": self.error_msg or "",
            "started_at": _fmt_dt(self.started_at),
            "finished_at": _fmt_dt(self.finished_at),
            "progress_pct": round(self.processed / self.total * 100, 1) if self.total else 0,
            "duration_sec": dur,
        }


class ArchiveJob(Base):
    __tablename__ = "archive_jobs"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, nullable=False, index=True)
    group_name = Column(Text, default="")
    action = Column(String(16), default="archive")
    status = Column(String(16), default="running")
    archive_path = Column(Text, nullable=True)
    archive_size_bytes = Column(Float, nullable=True)
    error_msg = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        dur = None
        if self.started_at and self.finished_at:
            dur = round((self.finished_at - self.started_at).total_seconds(), 1)
        return {
            "id": self.id,
            "group_id": self.group_id,
            "group_name": self.group_name or "",
            "action": self.action,
            "status": self.status,
            "archive_path": self.archive_path or "",
            "archive_size_bytes": self.archive_size_bytes,
            "archive_size_human": (
                _human_size(self.archive_size_bytes or 0) if self.archive_size_bytes else ""
            ),
            "error_msg": self.error_msg or "",
            "started_at": _fmt_dt(self.started_at),
            "finished_at": _fmt_dt(self.finished_at),
            "duration_sec": dur,
        }


class DedupEntry(Base):
    __tablename__ = "dedup_entries"

    id = Column(Integer, primary_key=True, index=True)
    sha256 = Column(String(64), nullable=False, unique=True, index=True)
    shared_path = Column(Text, nullable=False)
    dll_name = Column(String(512), default="")
    size_bytes = Column(Float, default=0)
    link_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sha256": self.sha256,
            "shared_path": self.shared_path,
            "dll_name": self.dll_name or "",
            "size_bytes": self.size_bytes,
            "size_human": _human_size(self.size_bytes or 0),
            "link_count": self.link_count or 0,
            "created_at": _fmt_dt(self.created_at),
        }


class DedupLink(Base):
    __tablename__ = "dedup_links"

    id = Column(Integer, primary_key=True, index=True)
    dedup_entry_id = Column(Integer, nullable=False, index=True)
    linked_path = Column(Text, nullable=False, unique=True)
    group_id = Column(Integer, nullable=True, index=True)
    link_type = Column(String(16), default="hardlink")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fmt_dt(dt: datetime.datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _human_size(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


# ── Table creation ────────────────────────────────────────────────────────────


def init_db():
    logger.info("Initialising database at %s", DB_PATH)
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()
    logger.info("Database ready.")


def _migrate_add_columns():
    """Idempotent ALTER TABLE statements for columns added after initial release."""
    migrations = [
        "ALTER TABLE file_groups ADD COLUMN file_tree_json TEXT",
        "ALTER TABLE file_groups ADD COLUMN is_archived INTEGER DEFAULT 0",
        "ALTER TABLE file_groups ADD COLUMN archive_path TEXT",
        "ALTER TABLE file_groups ADD COLUMN archived_at DATETIME",
        "ALTER TABLE file_groups ADD COLUMN archive_size_bytes REAL",
        "CREATE INDEX IF NOT EXISTS ix_file_groups_category ON file_groups (category)",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass
