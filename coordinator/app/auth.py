"""
JWT RS256 Authentication Module for StreamrP2P Coordinator.

Provides asymmetric JWT signing/verification using RSA keys,
FastAPI dependencies for route protection, and JWKS endpoint support.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# --- Constants ---

TOKEN_EXPIRY_HOURS = 24
ISSUER = "streamr-coordinator"
ALGORITHM = "RS256"

# --- Dataclass ---


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user extracted from a valid JWT."""

    user_id: str
    node_id: Optional[str] = None
    role: str = "node"
    stream_ids: List[str] = field(default_factory=list)


# --- Key Management ---

_private_key = None
_public_key = None


def _load_keys():
    """
    Load RSA key pair for JWT signing/verification.

    Priority:
    1. JWT_PRIVATE_KEY / JWT_PUBLIC_KEY env vars (PEM-encoded strings)
    2. Auto-generate a dev key pair (with warning)
    """
    global _private_key, _public_key

    private_pem = os.getenv("JWT_PRIVATE_KEY")
    public_pem = os.getenv("JWT_PUBLIC_KEY")

    if private_pem and public_pem:
        # Replace literal \n with actual newlines (common in env vars)
        private_pem = private_pem.replace("\\n", "\n")
        public_pem = public_pem.replace("\\n", "\n")
        _private_key = serialization.load_pem_private_key(
            private_pem.encode(), password=None
        )
        _public_key = serialization.load_pem_public_key(public_pem.encode())
        logger.info("Loaded RSA key pair from environment variables")
    else:
        logger.warning(
            "JWT_PRIVATE_KEY / JWT_PUBLIC_KEY not set — generating ephemeral dev key pair. "
            "DO NOT use in production."
        )
        _private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        _public_key = _private_key.public_key()


def get_private_key():
    """Return the loaded RSA private key, loading on first access."""
    if _private_key is None:
        _load_keys()
    return _private_key


def get_public_key():
    """Return the loaded RSA public key, loading on first access."""
    if _public_key is None:
        _load_keys()
    return _public_key


# --- JWT Encode / Decode ---


def encode_jwt(
    user_id: str,
    role: str,
    node_id: Optional[str] = None,
    stream_ids: Optional[List[str]] = None,
) -> str:
    """
    Create a signed RS256 JWT.

    Args:
        user_id: The subject (sub) claim — user identity ID.
        role: "streamer" or "node".
        node_id: Optional node identifier (for node tokens).
        stream_ids: Optional list of authorized stream IDs.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "stream_ids": stream_ids or [],
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iss": ISSUER,
    }
    if node_id is not None:
        payload["node_id"] = node_id

    return jwt.encode(payload, get_private_key(), algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict:
    """
    Decode and verify an RS256 JWT.

    Args:
        token: The raw JWT string.

    Returns:
        Decoded payload dict.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is invalid (bad signature, issuer, etc.).
    """
    return jwt.decode(
        token,
        get_public_key(),
        algorithms=[ALGORITHM],
        issuer=ISSUER,
    )


# --- FastAPI Dependencies ---

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts and validates the JWT from the
    Authorization: Bearer header, returning an AuthenticatedUser.
    """
    try:
        payload = decode_jwt(credentials.credentials)
        return AuthenticatedUser(
            user_id=payload["sub"],
            node_id=payload.get("node_id"),
            role=payload.get("role", "node"),
            stream_ids=payload.get("stream_ids", []),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_streamer(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Dependency that ensures the authenticated user has the streamer role."""
    if user.role != "streamer":
        raise HTTPException(status_code=403, detail="Streamer role required")
    return user


# --- JWKS Endpoint Helper ---


def get_jwks() -> dict:
    """
    Return a JWKS (JSON Web Key Set) representation of the public key.

    Used by the ``GET /api/v1/auth/.well-known/jwks.json`` endpoint so that
    external services (e.g. Go node clients) can verify tokens without
    sharing the private key.
    """
    import base64

    pub = get_public_key()
    pub_numbers = pub.public_numbers()

    def _int_to_base64url(n: int) -> str:
        byte_length = (n.bit_length() + 7) // 8
        return (
            base64.urlsafe_b64encode(n.to_bytes(byte_length, byteorder="big"))
            .rstrip(b"=")
            .decode()
        )

    return {
        "keys": [
            {
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": _int_to_base64url(pub_numbers.n),
                "e": _int_to_base64url(pub_numbers.e),
            }
        ]
    }
