"""
Tests for stream key management endpoints (task 2.4).

Covers:
- POST /api/v1/streams/{stream_id}/authorize-node
- POST /api/v1/streams/{stream_id}/regenerate-key
- POST /api/v1/srs/on-publish
"""

import os

# Must set DATABASE_URL before any app imports to avoid psycopg2 dependency
os.environ["DATABASE_URL"] = "sqlite:///./test_stream_routes.db"
# Disable Redis-backed rate limiter (no Redis in test env)
os.environ.pop("REDIS_URL", None)

import secrets
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.auth import AuthenticatedUser, encode_jwt
from app.database import get_db

# Patch the scheduler before importing app so the lifespan is harmless
import app.main as _main_module

_main_module.scheduler = type(_main_module.scheduler)()  # fresh scheduler instance

# Also neuter the limiter — use memory storage so no Redis needed
_main_module.limiter._storage_uri = "memory://"

from app.main import app
from app.models import Base, Stream, StreamAuthorization, UserIdentity

# ---------------------------------------------------------------------------
# Test DB setup (in-memory SQLite)
# ---------------------------------------------------------------------------

SQLALCHEMY_TEST_URL = "sqlite:///./test_stream_routes.db"
engine = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
)

# SQLite doesn't support PostgreSQL ARRAY type — register a custom compiler
from sqlalchemy import ARRAY, String as SAString
from sqlalchemy.ext.compiler import compiles


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"


TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """Single TestClient for the whole module — avoids scheduler lifecycle issues."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_streamer(db) -> UserIdentity:
    user = UserIdentity(
        display_name="test-streamer",
        email="streamer@test.com",
        role="streamer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_node_user(db) -> UserIdentity:
    user = UserIdentity(
        display_name="test-node-user",
        role="node",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_stream(db, owner: UserIdentity) -> Stream:
    stream = Stream(
        stream_id="test-stream-1",
        owner_user_id=owner.user_id,
        stream_key=secrets.token_urlsafe(32),
        rtmp_url="rtmp://localhost/live/test-stream-1",
        status="READY",
    )
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return stream


def _streamer_token(user: UserIdentity) -> dict:
    token = encode_jwt(user_id=user.user_id, role="streamer")
    return {"Authorization": f"Bearer {token}"}


def _node_token(user: UserIdentity, node_id: str = "node-1") -> dict:
    token = encode_jwt(user_id=user.user_id, role="node", node_id=node_id)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/v1/streams/{stream_id}/authorize-node
# ---------------------------------------------------------------------------


class TestAuthorizeNode:
    def test_authorize_node_success(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)
        node_user = _create_node_user(db)

        resp = client.post(
            f"/api/v1/streams/{stream.stream_id}/authorize-node",
            json={"user_id": node_user.user_id},
            headers=_streamer_token(streamer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stream_id"] == stream.stream_id
        assert data["user_id"] == node_user.user_id
        assert data["authorized_by"] == streamer.user_id

    def test_authorize_node_duplicate(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)
        node_user = _create_node_user(db)

        client.post(
            f"/api/v1/streams/{stream.stream_id}/authorize-node",
            json={"user_id": node_user.user_id},
            headers=_streamer_token(streamer),
        )
        resp = client.post(
            f"/api/v1/streams/{stream.stream_id}/authorize-node",
            json={"user_id": node_user.user_id},
            headers=_streamer_token(streamer),
        )
        assert resp.status_code == 409

    def test_authorize_node_not_owner(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)
        other = UserIdentity(
            display_name="other-streamer",
            email="other@test.com",
            role="streamer",
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        node_user = _create_node_user(db)
        resp = client.post(
            f"/api/v1/streams/{stream.stream_id}/authorize-node",
            json={"user_id": node_user.user_id},
            headers=_streamer_token(other),
        )
        assert resp.status_code == 403

    def test_authorize_node_stream_not_found(self, db, client):
        streamer = _create_streamer(db)
        resp = client.post(
            "/api/v1/streams/nonexistent/authorize-node",
            json={"user_id": "some-user"},
            headers=_streamer_token(streamer),
        )
        assert resp.status_code == 404

    def test_authorize_node_user_not_found(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)
        resp = client.post(
            f"/api/v1/streams/{stream.stream_id}/authorize-node",
            json={"user_id": "nonexistent-user"},
            headers=_streamer_token(streamer),
        )
        assert resp.status_code == 404

    def test_authorize_node_requires_streamer_role(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)
        node_user = _create_node_user(db)

        resp = client.post(
            f"/api/v1/streams/{stream.stream_id}/authorize-node",
            json={"user_id": node_user.user_id},
            headers=_node_token(node_user),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/v1/streams/{stream_id}/regenerate-key
# ---------------------------------------------------------------------------


class TestRegenerateKey:
    def test_regenerate_key_success(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)
        old_key = stream.stream_key

        resp = client.post(
            f"/api/v1/streams/{stream.stream_id}/regenerate-key",
            headers=_streamer_token(streamer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stream_id"] == stream.stream_id
        assert data["stream_key"] != old_key
        assert len(data["stream_key"]) > 20

    def test_regenerate_key_not_owner(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)
        other = UserIdentity(
            display_name="other",
            email="other2@test.com",
            role="streamer",
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        resp = client.post(
            f"/api/v1/streams/{stream.stream_id}/regenerate-key",
            headers=_streamer_token(other),
        )
        assert resp.status_code == 403

    def test_regenerate_key_stream_not_found(self, db, client):
        streamer = _create_streamer(db)
        resp = client.post(
            "/api/v1/streams/nonexistent/regenerate-key",
            headers=_streamer_token(streamer),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/srs/on-publish
# ---------------------------------------------------------------------------


class TestSrsOnPublish:
    def test_on_publish_valid_key(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)

        resp = client.post(
            "/api/v1/srs/on-publish",
            json={"param": f"?key={stream.stream_key}"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_on_publish_invalid_key(self, db, client):
        resp = client.post(
            "/api/v1/srs/on-publish",
            json={"param": "?key=totally-invalid-key"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] != 0

    def test_on_publish_missing_key(self, db, client):
        resp = client.post(
            "/api/v1/srs/on-publish",
            json={"param": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] != 0

    def test_on_publish_no_param(self, db, client):
        resp = client.post(
            "/api/v1/srs/on-publish",
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] != 0

    def test_on_publish_key_without_question_mark(self, db, client):
        streamer = _create_streamer(db)
        stream = _create_stream(db, streamer)

        resp = client.post(
            "/api/v1/srs/on-publish",
            json={"param": f"key={stream.stream_key}"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
