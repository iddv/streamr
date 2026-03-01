"""
Authentication endpoints for StreamrP2P Coordinator.

Provides streamer registration/login (email+password) and node registration
(stream_key) flows, token refresh, and JWKS public key endpoint.
"""

import logging
import os
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import (
    AuthenticatedUser,
    encode_jwt,
    get_current_user,
    get_jwks,
)
from .database import get_db
from .models import Node, Stream, UserAccount, UserIdentity
from .headscale_client import get_headscale_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class StreamerRegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class NodeRegisterRequest(BaseModel):
    node_id: str
    stream_key: str
    display_name: str = ""


class AuthResponse(BaseModel):
    token: str
    user_id: str
    role: str
    stream_id: Optional[str] = None
    node_id: Optional[str] = None
    headscale_auth_key: Optional[str] = None
    headscale_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _ensure_user_account(db: Session, user_id: str) -> UserAccount:
    """Create a UserAccount for the given user_id if one doesn't exist."""
    account = db.query(UserAccount).filter(UserAccount.user_id == user_id).first()
    if not account:
        account = UserAccount(user_id=user_id)
        db.add(account)
    return account


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register-streamer", response_model=AuthResponse)
async def register_streamer(
    body: StreamerRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new streamer with email + password.

    Creates a UserIdentity (role=streamer) and a UserAccount, then returns a JWT.
    """
    # Check for duplicate email
    existing = (
        db.query(UserIdentity)
        .filter(UserIdentity.email == body.email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = UserIdentity(
        display_name=body.display_name,
        email=body.email,
        hashed_password=_hash_password(body.password),
        role="streamer",
    )
    db.add(user)
    db.flush()  # populate user.user_id

    _ensure_user_account(db, user.user_id)
    db.commit()
    db.refresh(user)

    token = encode_jwt(user_id=user.user_id, role="streamer")
    logger.info("Streamer registered: %s (%s)", user.display_name, user.user_id)

    return AuthResponse(token=token, user_id=user.user_id, role="streamer")


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate a streamer with email + password and return a JWT.
    """
    user = (
        db.query(UserIdentity)
        .filter(UserIdentity.email == body.email)
        .first()
    )
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Build stream_ids list for the token
    stream_ids = [s.stream_id for s in getattr(user, "owned_streams", [])]

    token = encode_jwt(
        user_id=user.user_id,
        role=user.role,
        stream_ids=stream_ids,
    )
    logger.info("Streamer logged in: %s", user.user_id)

    return AuthResponse(token=token, user_id=user.user_id, role=user.role)


@router.post("/register", response_model=AuthResponse)
async def register_node(
    body: NodeRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a node using a stream_key shared out-of-band by the streamer.

    Validates the stream_key, creates or finds a UserIdentity, creates a
    Node record, and returns a JWT scoped for node operations.
    """
    # Validate stream_key
    stream = (
        db.query(Stream)
        .filter(Stream.stream_key == body.stream_key)
        .first()
    )
    if not stream:
        raise HTTPException(status_code=401, detail="Invalid stream key")

    # Find or create UserIdentity for this node operator
    display_name = body.display_name or body.node_id
    user = (
        db.query(UserIdentity)
        .filter(
            UserIdentity.display_name == display_name,
            UserIdentity.role == "node",
        )
        .first()
    )
    if not user:
        user = UserIdentity(
            display_name=display_name,
            role="node",
        )
        db.add(user)
        db.flush()

    _ensure_user_account(db, user.user_id)

    # Create Node record if it doesn't already exist for this (node_id, stream_id)
    existing_node = (
        db.query(Node)
        .filter(Node.node_id == body.node_id, Node.stream_id == stream.stream_id)
        .first()
    )
    if not existing_node:
        node = Node(
            node_id=body.node_id,
            stream_id=stream.stream_id,
            user_id=user.user_id,
            stats_url="",  # will be set on first heartbeat
            status="active",
        )
        db.add(node)

    db.commit()
    db.refresh(user)

    token = encode_jwt(
        user_id=user.user_id,
        role="node",
        node_id=body.node_id,
        stream_ids=[stream.stream_id],
    )

    # Create a Headscale pre-auth key for VPN mesh joining
    headscale_auth_key = None
    try:
        hs_client = get_headscale_client()
        headscale_auth_key = await hs_client.create_preauth_key(
            expiry_hours=24, reusable=False
        )
    except Exception:
        logger.warning("Failed to create Headscale auth key for node %s", body.node_id, exc_info=True)

    logger.info(
        "Node registered: node_id=%s stream=%s user=%s headscale_key=%s",
        body.node_id,
        stream.stream_id,
        user.user_id,
        "provided" if headscale_auth_key else "none",
    )

    return AuthResponse(
        token=token,
        user_id=user.user_id,
        role="node",
        stream_id=stream.stream_id,
        node_id=body.node_id,
        headscale_auth_key=headscale_auth_key,
        headscale_url=os.getenv("HEADSCALE_PUBLIC_URL", os.getenv("HEADSCALE_URL", "")) if headscale_auth_key else None,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Issue a fresh JWT for an already-authenticated user.
    """
    token = encode_jwt(
        user_id=current_user.user_id,
        role=current_user.role,
        node_id=current_user.node_id,
        stream_ids=current_user.stream_ids,
    )
    return AuthResponse(
        token=token,
        user_id=current_user.user_id,
        role=current_user.role,
        node_id=current_user.node_id,
    )


@router.get("/.well-known/jwks.json")
async def jwks_endpoint():
    """
    Serve the public key in JWKS format so external services (e.g. Go node
    clients) can verify JWTs without sharing the private key.
    """
    return get_jwks()
