"""
HLS proxy — forwards viewer requests to friend nodes over the VPN mesh.
Tasks 4.8, 4.9 — Req 11.1, 12.2–12.4, Design §14, §15
"""

import logging
import os

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from .redis_state import get_redis, get_stream_nodes

logger = logging.getLogger(__name__)

router = APIRouter(tags=["proxy"])

SRS_HOST = os.getenv("SRS_HOST", "localhost")
SRS_PORT = os.getenv("SRS_PORT", "8080")

# Shared async client — reused across requests for connection pooling
_http_client: httpx.AsyncClient | None = None


async def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=5.0)
    return _http_client


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


async def _get_viewer_assignment(stream_id: str, viewer_key: str) -> str | None:
    """Look up which node a viewer is assigned to."""
    try:
        r = await get_redis()
        return await r.hget(f"stream:{stream_id}:viewers", viewer_key)
    except Exception:
        logger.warning("Redis unavailable for viewer lookup", exc_info=True)
        return None


async def _reassign_viewer(stream_id: str, viewer_key: str) -> str | None:
    """
    Try to assign the viewer to a different node.
    Returns the new node's VPN IP or None if no nodes available.
    """
    try:
        r = await get_redis()
        nodes = await get_stream_nodes(r, stream_id)
    except Exception:
        return None

    candidates = [
        n for n in nodes
        if n.get("capacity_pct", 0) < 90
        and n.get("trust_score", 0) >= 0.5
    ]
    if not candidates:
        return None

    candidates.sort(
        key=lambda n: (-n.get("trust_score", 0), n.get("viewer_count", 0))
    )
    best = candidates[0]
    node_id = best["node_id"]

    try:
        await r.hset(f"stream:{stream_id}:viewers", viewer_key, node_id)
    except Exception:
        pass

    return best.get("vpn_ip")


async def _resolve_node_vpn_ip(stream_id: str, node_id: str) -> str | None:
    """Look up a node's VPN IP from Redis."""
    try:
        r = await get_redis()
        nodes = await get_stream_nodes(r, stream_id)
        for n in nodes:
            if n["node_id"] == node_id:
                return n.get("vpn_ip")
    except Exception:
        pass
    return None


def _viewer_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/api/v1/proxy/{stream_id}/{path:path}")
async def proxy_hls(stream_id: str, path: str, request: Request):
    """
    Proxy HLS requests to the assigned friend node over the VPN mesh.
    Falls back to SRS on node failure.
    """
    viewer_key = _viewer_key(request)
    node_id = await _get_viewer_assignment(stream_id, viewer_key)

    vpn_ip: str | None = None
    if node_id:
        vpn_ip = await _resolve_node_vpn_ip(stream_id, node_id)

    if not vpn_ip:
        # No assignment or node gone — try reassignment
        vpn_ip = await _reassign_viewer(stream_id, viewer_key)

    if vpn_ip:
        node_url = f"http://{vpn_ip}:8080/live/{stream_id}/{path}"
        try:
            client = await _get_http_client()
            resp = await client.get(node_url)
            if resp.status_code == 200:
                return StreamingResponse(
                    content=resp.aiter_bytes(),
                    media_type=resp.headers.get("content-type", "application/octet-stream"),
                    status_code=200,
                )
            else:
                _log_fallback(stream_id, "node_offline")
                logger.warning(
                    "Node %s returned %d for %s, falling back to SRS",
                    node_id, resp.status_code, path,
                )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            _log_fallback(stream_id, "node_offline")
            logger.warning(
                "Node %s unreachable (%s), falling back to SRS",
                node_id, type(exc).__name__,
            )
    else:
        _log_fallback(stream_id, "no_active_nodes")

    # SRS fallback — translate from subdirectory-style paths (used by Go node)
    # to SRS flat HLS layout: /live/{stream}.m3u8 and /live/{stream}-{seq}.ts
    if path == "index.m3u8":
        srs_path = f"{stream_id}.m3u8"
    else:
        srs_path = path
    srs_url = f"http://{SRS_HOST}:{SRS_PORT}/live/{srs_path}"
    try:
        client = await _get_http_client()
        resp = await client.get(srs_url)
        return StreamingResponse(
            content=resp.aiter_bytes(),
            media_type=resp.headers.get("content-type", "application/octet-stream"),
            status_code=resp.status_code,
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Stream unavailable")
