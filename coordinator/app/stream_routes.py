"""
Stream Key Management endpoints for StreamrP2P Coordinator.

Provides stream-key-related operations:
- POST /api/v1/streams/{stream_id}/authorize-node  — owner authorizes a user
- POST /api/v1/streams/{stream_id}/regenerate-key   — owner regenerates stream key
- POST /api/v1/srs/on-publish                       — SRS RTMP auth callback
"""

import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import AuthenticatedUser, get_current_user, require_streamer
from .database import get_db
from .models import Stream, StreamAuthorization, UserIdentity

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streams"])

# ---------------------------------------------------------------------------
# Request / Response schemas (local to this module)
# ---------------------------------------------------------------------------


class AuthorizeNodeRequest(BaseModel):
    user_id: str


class AuthorizeNodeResponse(BaseModel):
    stream_id: str
    user_id: str
    authorized_at: datetime
    authorized_by: str

    class Config:
        from_attributes = True


class RegenerateKeyResponse(BaseModel):
    stream_id: str
    stream_key: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_owned_stream(
    stream_id: str, user: AuthenticatedUser, db: Session
) -> Stream:
    """Fetch a stream and verify the current user is the owner."""
    stream = (
        db.query(Stream).filter(Stream.stream_id == stream_id).first()
    )
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not the stream owner")
    return stream


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/streams/{stream_id}/authorize-node",
    response_model=AuthorizeNodeResponse,
)
async def authorize_node(
    stream_id: str,
    body: AuthorizeNodeRequest,
    user: AuthenticatedUser = Depends(require_streamer),
    db: Session = Depends(get_db),
):
    """
    Explicitly authorize a user to register nodes against this stream.

    Only the stream owner (streamer) can call this endpoint.
    """
    stream = _get_owned_stream(stream_id, user, db)

    # Verify the target user exists
    target_user = (
        db.query(UserIdentity)
        .filter(UserIdentity.user_id == body.user_id)
        .first()
    )
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for existing authorization
    existing = (
        db.query(StreamAuthorization)
        .filter(
            StreamAuthorization.stream_id == stream.stream_id,
            StreamAuthorization.user_id == body.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="User already authorized for this stream"
        )

    auth = StreamAuthorization(
        stream_id=stream.stream_id,
        user_id=body.user_id,
        authorized_by=user.user_id,
    )
    db.add(auth)
    db.commit()
    db.refresh(auth)

    logger.info(
        "Node authorization granted: stream=%s user=%s by=%s",
        stream.stream_id,
        body.user_id,
        user.user_id,
    )

    return AuthorizeNodeResponse(
        stream_id=stream.stream_id,
        user_id=body.user_id,
        authorized_at=auth.authorized_at,
        authorized_by=auth.authorized_by,
    )


@router.post(
    "/api/v1/streams/{stream_id}/regenerate-key",
    response_model=RegenerateKeyResponse,
)
async def regenerate_stream_key(
    stream_id: str,
    user: AuthenticatedUser = Depends(require_streamer),
    db: Session = Depends(get_db),
):
    """
    Regenerate the stream key, invalidating the previous one.

    Only the stream owner (streamer) can call this endpoint.
    """
    stream = _get_owned_stream(stream_id, user, db)

    stream.stream_key = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(stream)

    logger.info("Stream key regenerated: stream=%s by=%s", stream_id, user.user_id)

    return RegenerateKeyResponse(
        stream_id=stream.stream_id,
        stream_key=stream.stream_key,
    )


@router.post("/api/v1/srs/on-publish")
async def srs_on_publish(request: Request, db: Session = Depends(get_db)):
    """
    SRS on_publish HTTP callback for RTMP ingest authentication.

    SRS sends a POST with form/JSON body containing the stream name and
    query parameters. The stream key is expected as the ``?key=`` query
    parameter on the RTMP URL (e.g. rtmp://host/live/stream_id?key=<stream_key>).

    Returns HTTP 200 (allow) or HTTP 403 (reject).
    """
    # SRS may send JSON or form-encoded body
    try:
        body = await request.json()
    except Exception:
        body = {}

    # SRS provides the RTMP query string in the "param" field
    # e.g. "?key=abc123" — extract the key value
    param = body.get("param", "")
    stream_key = _extract_key_from_param(param)

    if not stream_key:
        logger.warning("SRS on_publish: missing stream key in param=%r", param)
        # SRS expects JSON with non-zero code to reject
        return JSONResponse(status_code=200, content={"code": 1, "msg": "Missing stream key"})

    # Validate the stream key
    stream = (
        db.query(Stream).filter(Stream.stream_key == stream_key).first()
    )
    if not stream:
        logger.warning("SRS on_publish: invalid stream key")
        return JSONResponse(status_code=200, content={"code": 1, "msg": "Invalid stream key"})

    logger.info(
        "SRS on_publish: authorized stream=%s", stream.stream_id
    )
    # SRS expects JSON with code=0 to allow publish
    return JSONResponse(status_code=200, content={"code": 0})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_key_from_param(param: str) -> str | None:
    """
    Parse the ``key`` value from an SRS ``param`` string.

    SRS sends the RTMP URL query string as-is, e.g. ``?key=abc123``.
    """
    if not param:
        return None

    from urllib.parse import parse_qs, urlparse

    # param may or may not start with '?'
    qs = param.lstrip("?")
    parsed = parse_qs(qs)
    keys = parsed.get("key", [])
    return keys[0] if keys else None
