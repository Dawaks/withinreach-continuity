"""Shared pytest fixtures: in-memory SQLite database and seeded demo data."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.demo.seed import seed_demo_data

# Import models so they register with Base.metadata.
from app import models  # noqa: F401


@pytest.fixture
def db():
    """Fresh in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_db(db):
    """In-memory database populated with the Grace Community Church demo data."""
    seed_demo_data(db)
    return db


@pytest.fixture
def client(tmp_path):
    """FastAPI test client backed by a seeded temporary file database.

    A temp file DB (not :memory:) is used so the connection/tables are shared
    across the request threads TestClient uses. get_db is overridden to use
    this engine; the app lifespan is not triggered.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import get_db
    from app.main import app

    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed demo data once.
    seed_session = TestSession()
    seed_demo_data(seed_session)
    seed_session.close()

    def _override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    # Expose a session for assertions in tests.
    app.dependency_overrides[get_db] = _override_get_db
    c = TestClient(app)
    c._test_session_factory = TestSession  # type: ignore[attr-defined]
    try:
        yield c
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
