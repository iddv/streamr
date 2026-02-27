"""
Viewer routing — assigns viewers to the best available friend node.
Tasks 4.7, 4.9 — Req 11.1–11.5, 12.1, 12.3, 12.4, Design §14, §15
"""

import logging
import os
from decimal import Decimal

from fastapi import APIRouter, Request

from .redis_state import get_redis, get_stream_nodes

logger = logging.getLogger(__name__)

router = APIRouter(tags=["viewer"])

SRS_HOST = os.getenv("SRS_HOST", "localhost")
SRS_PORT = os.getenv("SRS_PORT", "8080")


def _log_fallback(stream_id: str, reason: str) -> None:
    """Structured log for every SRS fallback event (Req 12.3)."""
    logger.info(
        "SRS fallback triggered",
        extra={
            "event": "srs_fallback",
            "stream_id": stream_id,
            "reason": reason,
        },
    )


async def _pick_best_node(stream_id: str) -> dict | None:
    """
    Select the best friend node for a viewer:
    1. Filter out saturated nodes (capacity_pct >= 90)
    2. Filter out low-trust nodes (trust_score < 0.5)
    3. Among remaining, pick highest trust_score; break ties by lowest viewer_count
    """
    try:
        r = await get_redis()
        nodes = await get_stream_nodes(r, stream_id)
    except Exception:
        logger.warning("Redis unavailable for viewer routing", exc_info=True)
        return None

    candidates = [
        n for n in nodes
        if n.get("capacity_pct", 0) < 90
        and n.get("trust_score", 0) >= 0.5
    ]

    if not candidates:
        return None

    # Sort: highest trust first, then lowest viewer_count
    candidates.sort(
        key=lambda n: (-n.get("trust_score", 0), n.get("viewer_count", 0))
    )
    return candidates[0]


async def _record_viewer_assignment(
    stream_id: str, viewer_key: str, node_id: str
) -> None:
    """Store viewer→node mapping in Redis for proxy lookups."""
    try:
        r = await get_redis()
        await r.hset(f"stream:{stream_id}:viewers", viewer_key, node_id)
    except Exception:
        logger.warning("Failed to record viewer assignment", exc_info=True)


def _viewer_key(request: Request) -> str:
    """Derive a viewer identifier from the request (IP-based for MVP)."""
    return request.client.host if request.client else "unknown"


@router.get("/api/v1/watch/{stream_id}")
async def watch_stream(stream_id: str, request: Request):
    """
    Return the optimal source URL for a viewer.
    Picks the best friend node or falls back to SRS direct HLS.
    """
    node = await _pick_best_node(stream_id)

    if node:
        node_id = node["node_id"]
        viewer_key = _viewer_key(request)
        await _record_viewer_assignment(stream_id, viewer_key, node_id)

        return {
            "source_url": f"/api/v1/proxy/{stream_id}/index.m3u8",
            "source_type": "friend_node",
            "node_id": node_id,
        }

    # Fallback to SRS
    _log_fallback(stream_id, "no_active_nodes")
    return {
        "source_url": f"http://{SRS_HOST}:{SRS_PORT}/live/{stream_id}.m3u8",
        "source_type": "srs",
        "node_id": None,
    }
