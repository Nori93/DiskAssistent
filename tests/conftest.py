"""
Shared pytest fixtures for DiskAssistent integration tests.

Uses an in-memory SQLite database so tests are fully isolated and never
touch the real diskassistent.db on disk.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Make sure project root is importable (mirrors main.py behaviour)
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Base, FileGroup, FileRecord, get_db

# ── In-memory DB engine ───────────────────────────────────────────────────────


def _make_in_memory_engine():
    # StaticPool: all connections share one underlying connection so tables
    # created by create_all are visible to every session within the same test.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def db_engine():
    """Fresh in-memory SQLite engine per test."""
    engine = _make_in_memory_engine()
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Transactional session that rolls back after each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient wired to the FastAPI app with the in-memory DB injected
    via dependency override.
    """
    # Import app lazily so the real init_db() has already run once at module
    # level and we only override get_db going forward.
    import main as app_module

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # session lifetime managed by the fixture

    app_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(app_module.app, raise_server_exceptions=True) as c:
        yield c
    app_module.app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────


def make_file(db_session, **kwargs) -> FileRecord:
    """Insert a minimal FileRecord and return it."""
    defaults = {
        "name": "test_file.txt",
        "full_path": "/tmp/test_file.txt",
        "parent_dir": "/tmp",
        "extension": ".txt",
        "size_bytes": 1024,
        "category": "Documents",
        "ai_category": "Documents",
        "category_overridden": False,
        "tags": "",
        "description": "",
        "thumbnail_path": "",
        "is_missing": False,
    }
    defaults.update(kwargs)
    rec = FileRecord(**defaults)
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    return rec


def make_group(db_session, **kwargs) -> FileGroup:
    """Insert a minimal FileGroup and return it."""
    defaults = {
        "name": "TestGroup",
        "root_path": "/tmp/TestGroup",
        "category": "Other",
        "description": "",
        "thumbnail_path": "",
        "file_tree_json": None,
    }
    defaults.update(kwargs)
    grp = FileGroup(**defaults)
    db_session.add(grp)
    db_session.commit()
    db_session.refresh(grp)
    return grp
