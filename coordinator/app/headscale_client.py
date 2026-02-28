"""
Headscale Admin API client for StreamrP2P Coordinator.

Manages pre-auth key creation and mesh node listing via the Headscale
gRPC-gateway REST API.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

HEADSCALE_URL = os.getenv("HEADSCALE_URL", "http://localhost:8080")
HEADSCALE_API_KEY = os.getenv("HEADSCALE_API_KEY", "")
HEADSCALE_API_KEY_SECRET_NAME = os.getenv("HEADSCALE_API_KEY_SECRET_NAME", "")


def _resolve_api_key() -> str:
    """
    Resolve the Headscale API key.

    Priority: HEADSCALE_API_KEY env var > Secrets Manager lookup > empty string.
    """
    # Direct env var takes precedence
    if HEADSCALE_API_KEY:
        return HEADSCALE_API_KEY

    # Try Secrets Manager if secret name is configured
    if HEADSCALE_API_KEY_SECRET_NAME:
        try:
            import boto3
            client = boto3.client("secretsmanager", region_name=os.getenv("AWS_DEFAULT_REGION", "eu-west-1"))
            resp = client.get_secret_value(SecretId=HEADSCALE_API_KEY_SECRET_NAME)
            key = resp.get("SecretString", "")
            if key:
                logger.info("Loaded Headscale API key from Secrets Manager (%s)", HEADSCALE_API_KEY_SECRET_NAME)
                return key
        except Exception:
            logger.warning("Failed to load Headscale API key from Secrets Manager", exc_info=True)

    return ""


class HeadscaleClient:
    """Thin async wrapper around the Headscale admin REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or HEADSCALE_URL).rstrip("/")
        self.api_key = api_key or _resolve_api_key()
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10.0,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    async def create_preauth_key(
        self,
        expiry_hours: int = 24,
        reusable: bool = False,
        user: str = "default",
    ) -> Optional[str]:
        """
        Create a single-use (or reusable) pre-authentication key.

        Returns the key string, or None if Headscale is unavailable.
        """
        expiration = (
            datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        ).isoformat()

        payload = {
            "user": user,
            "reusable": reusable,
            "ephemeral": False,
            "expiration": expiration,
        }

        try:
            resp = await self._client.post("/api/v1/preauthkey", json=payload)
            resp.raise_for_status()
            data = resp.json()
            key = data.get("preAuthKey", {}).get("key")
            if key:
                logger.info("Created Headscale pre-auth key (expiry=%dh, reusable=%s)", expiry_hours, reusable)
            return key
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Headscale API error creating pre-auth key: %s %s",
                exc.response.status_code,
                exc.response.text,
            )
            return None
        except Exception:
            logger.warning("Headscale unavailable — skipping pre-auth key creation", exc_info=True)
            return None

    async def list_nodes(self) -> List[dict]:
        """
        List all nodes (machines) registered with Headscale.

        Returns a list of node dicts, or an empty list on failure.
        """
        try:
            resp = await self._client.get("/api/v1/machine")
            resp.raise_for_status()
            data = resp.json()
            machines = data.get("machines", [])
            return [
                {
                    "id": m.get("id"),
                    "name": m.get("name", m.get("givenName", "")),
                    "ip_addresses": m.get("ipAddresses", []),
                    "online": m.get("online", False),
                    "last_seen": m.get("lastSeen"),
                    "user": m.get("user", {}).get("name", ""),
                }
                for m in machines
            ]
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Headscale API error listing nodes: %s %s",
                exc.response.status_code,
                exc.response.text,
            )
            return []
        except Exception:
            logger.warning("Headscale unavailable — cannot list nodes", exc_info=True)
            return []

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()


# Module-level singleton (lazy)
_headscale_client: Optional[HeadscaleClient] = None


def get_headscale_client() -> HeadscaleClient:
    """Return a shared HeadscaleClient instance."""
    global _headscale_client
    if _headscale_client is None:
        _headscale_client = HeadscaleClient()
    return _headscale_client
