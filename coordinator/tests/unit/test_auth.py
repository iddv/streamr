"""
Unit tests for auth module — JWT creation, validation, expiry, refresh, error cases.
Task 7.6 — Req 21, Design §24, Properties 1–5
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt as pyjwt
import pytest

from app.auth import (
    ALGORITHM,
    ISSUER,
    TOKEN_EXPIRY_HOURS,
    AuthenticatedUser,
    decode_jwt,
    encode_jwt,
    get_jwks,
    get_private_key,
    get_public_key,
)


# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------


class TestKeyLoading:
    def test_auto_generates_dev_keys(self):
        """Ephemeral dev keys are generated when env vars are absent."""
        priv = get_private_key()
        pub = get_public_key()
        assert priv is not None
        assert pub is not None

    def test_keys_are_consistent(self):
        """Private and public keys form a valid pair."""
        token = encode_jwt(user_id="u1", role="node")
        payload = decode_jwt(token)
        assert payload["sub"] == "u1"


# ---------------------------------------------------------------------------
# encode_jwt
# ---------------------------------------------------------------------------


class TestEncodeJWT:
    def test_basic_token_creation(self):
        token = encode_jwt(user_id="user-1", role="streamer")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_payload_claims(self):
        token = encode_jwt(
            user_id="user-2",
            role="node",
            node_id="node-abc",
            stream_ids=["s1", "s2"],
        )
        payload = decode_jwt(token)
        assert payload["sub"] == "user-2"
        assert payload["role"] == "node"
        assert payload["node_id"] == "node-abc"
        assert payload["stream_ids"] == ["s1", "s2"]
        assert payload["iss"] == ISSUER


    def test_expiry_is_set(self):
        token = encode_jwt(user_id="u", role="node")
        payload = decode_jwt(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        delta = exp - iat
        assert delta == timedelta(hours=TOKEN_EXPIRY_HOURS)

    def test_node_id_omitted_when_none(self):
        token = encode_jwt(user_id="u", role="streamer")
        payload = decode_jwt(token)
        assert "node_id" not in payload

    def test_empty_stream_ids_default(self):
        token = encode_jwt(user_id="u", role="node")
        payload = decode_jwt(token)
        assert payload["stream_ids"] == []


# ---------------------------------------------------------------------------
# decode_jwt
# ---------------------------------------------------------------------------


class TestDecodeJWT:
    def test_valid_token(self):
        token = encode_jwt(user_id="u1", role="node")
        payload = decode_jwt(token)
        assert payload["sub"] == "u1"

    def test_expired_token_raises(self):
        """Manually craft an already-expired token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "u1",
            "role": "node",
            "stream_ids": [],
            "iat": now - timedelta(hours=48),
            "exp": now - timedelta(hours=1),
            "iss": ISSUER,
        }
        token = pyjwt.encode(payload, get_private_key(), algorithm=ALGORITHM)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_jwt(token)

    def test_wrong_issuer_raises(self):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "u1",
            "role": "node",
            "stream_ids": [],
            "iat": now,
            "exp": now + timedelta(hours=1),
            "iss": "wrong-issuer",
        }
        token = pyjwt.encode(payload, get_private_key(), algorithm=ALGORITHM)
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_jwt(token)

    def test_tampered_token_raises(self):
        token = encode_jwt(user_id="u1", role="node")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_jwt(tampered)

    def test_garbage_string_raises(self):
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_jwt("not.a.jwt")


# ---------------------------------------------------------------------------
# AuthenticatedUser dataclass
# ---------------------------------------------------------------------------


class TestAuthenticatedUser:
    def test_defaults(self):
        user = AuthenticatedUser(user_id="u1")
        assert user.role == "node"
        assert user.node_id is None
        assert user.stream_ids == []

    def test_custom_fields(self):
        user = AuthenticatedUser(
            user_id="u2", node_id="n1", role="streamer", stream_ids=["s1"]
        )
        assert user.node_id == "n1"
        assert user.role == "streamer"


# ---------------------------------------------------------------------------
# JWKS
# ---------------------------------------------------------------------------


class TestJWKS:
    def test_jwks_structure(self):
        jwks = get_jwks()
        assert "keys" in jwks
        assert len(jwks["keys"]) == 1
        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert key["use"] == "sig"
        assert "n" in key
        assert "e" in key
