"""
Shared pytest fixtures for coordinator tests.
Task 7.5 — Req 22.4, Design §24

Provides:
- test_db: isolated SQLAlchemy session backed by test PostgreSQL (port 5433)
- test_redis: isolated Redis client (port 6380)
- client: FastAPI TestClient with dependency overrides
- mock services for PayoutService, SpotCheckProber, etc.

DB-dependent tests auto-skip when PostgreSQL is unavailable (local dev).
CI provides PostgreSQL via service container so the full suite runs there.
"""

import os
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Override DATABASE_URL before any app imports
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://test_streamr:test_streamr@localhost:5433/test_streamr",
)
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6380/0")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL

from app.models import Base
from app import models
from app.database import get_db


# ---------------------------------------------------------------------------
# Auto-detect PostgreSQL availability
# ---------------------------------------------------------------------------

def _pg_is_available() -> bool:
    """Try to connect to the test PostgreSQL instance."""
    try:
        eng = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 2})
        conn = eng.connect()
        conn.close()
        eng.dispose()
        return True
    except Exception:
        return False


_PG_AVAILABLE = _pg_is_available()


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """Create a test engine once per session. Skips if PostgreSQL unavailable."""
    if not _PG_AVAILABLE:
        pytest.skip("PostgreSQL not available — DB tests run in CI")
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def test_db(engine):
    """Per-test transactional session — rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Redis fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_redis():
    """Return a mock Redis client for unit tests (no real Redis needed)."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.hset = AsyncMock()
    mock.hgetall = AsyncMock(return_value={})
    mock.delete = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(test_db):
    """TestClient with DB dependency overridden to use test_db."""
    from app import main as _main_mod
    from app.main import app

    # Replace the global scheduler with a fresh no-op instance so the
    # lifespan doesn't collide with other tests or fail on event-loop reuse.
    _main_mod.scheduler = type(_main_mod.scheduler)()

    def _override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Model factory helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_user(test_db):
    """Factory to create a UserIdentity + UserAccount."""
    def _make(user_id: str = "test-user-1", role: str = "node", trust: float = 0.75):
        identity = models.UserIdentity(
            user_id=user_id,
            display_name=f"Test {user_id}",
            role=role,
        )
        test_db.add(identity)
        test_db.flush()

        account = models.UserAccount(
            user_id=user_id,
            balance_usd=Decimal("0"),
            total_gb_relayed=Decimal("0"),
            earnings_last_30d=Decimal("0"),
            trust_score=Decimal(str(trust)),
            flags=[],
            last_updated_at=datetime.now(timezone.utc),
        )
        test_db.add(account)
        test_db.flush()
        return identity, account

    return _make


@pytest.fixture()
def make_stream(test_db):
    """Factory to create a Stream."""
    def _make(stream_id: str = "test-stream", owner_user_id: str = "test-user-1"):
        stream = models.Stream(
            stream_id=stream_id,
            owner_user_id=owner_user_id,
            stream_key="test-key-abc123",
            rtmp_url=f"rtmp://localhost:1935/live/{stream_id}",
            status="LIVE",
        )
        test_db.add(stream)
        test_db.flush()
        return stream

    return _make


@pytest.fixture()
def make_node(test_db):
    """Factory to create a Node."""
    def _make(
        node_id: str = "node-1",
        stream_id: str = "test-stream",
        user_id: str = "test-user-1",
    ):
        node = models.Node(
            node_id=node_id,
            stream_id=stream_id,
            user_id=user_id,
            stats_url=f"http://10.0.0.1:8080/stats",
            status="active",
        )
        test_db.add(node)
        test_db.flush()
        return node

    return _make
