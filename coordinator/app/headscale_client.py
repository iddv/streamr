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


class HeadscaleClient:
    """Thin async wrapper around the Headscale admin REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or HEADSCALE_URL).rstrip("/")
        self.api_key = api_key or HEADSCALE_API_KEY
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
