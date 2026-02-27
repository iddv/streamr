"""
Redis state management for chunk distribution.

Maintains per-stream node state in Redis hashes for fast peer lookups
and viewer routing decisions.

Keys:
  stream:{stream_id}:nodes   — hash: node_id → JSON{vpn_ip, trust_score, capacity_pct, viewer_count, last_heartbeat}
  stream:{stream_id}:viewers — hash: viewer_key → node_id
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return a shared async Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        url = REDIS_URL if REDIS_URL.startswith("redis") else f"redis://{REDIS_URL}"
        _redis_pool = aioredis.from_url(url, decode_responses=True)
    return _redis_pool


async def close_redis() -> None:
    """Close the shared Redis pool (call on shutdown)."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


async def update_node_state(
    r: aioredis.Redis,
    stream_id: str,
    node_id: str,
    vpn_ip: str,
    trust_score: float,
    capacity_pct: int,
    viewer_count: int,
) -> None:
    """Update a node's state in the stream's Redis hash."""
    key = f"stream:{stream_id}:nodes"
    value = json.dumps({
        "vpn_ip": vpn_ip or "",
        "trust_score": trust_score,
        "capacity_pct": capacity_pct,
        "viewer_count": viewer_count,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    })
    await r.hset(key, node_id, value)


async def get_stream_nodes(r: aioredis.Redis, stream_id: str) -> List[dict]:
    """Return all nodes for a stream, each dict includes node_id."""
    key = f"stream:{stream_id}:nodes"
    raw = await r.hgetall(key)
    nodes = []
    for node_id, data_str in raw.items():
        try:
            data = json.loads(data_str)
            data["node_id"] = node_id
            nodes.append(data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Corrupt Redis entry for node %s in stream %s", node_id, stream_id)
    return nodes


async def remove_node(r: aioredis.Redis, stream_id: str, node_id: str) -> None:
    """Remove a node from the stream's Redis hash."""
    key = f"stream:{stream_id}:nodes"
    await r.hdel(key, node_id)


async def cleanup_stale_nodes(r: aioredis.Redis, max_age_seconds: int = 90) -> int:
    """
    Scan all stream node hashes and remove entries whose last_heartbeat
    is older than *max_age_seconds*.  Returns the number of removed entries.
    """
    removed = 0
    now = datetime.now(timezone.utc)
    cursor = "0"
    while True:
        cursor, keys = await r.scan(cursor=cursor, match="stream:*:nodes", count=100)
        for key in keys:
            entries = await r.hgetall(key)
            for node_id, data_str in entries.items():
                try:
                    data = json.loads(data_str)
                    last_hb = datetime.fromisoformat(data["last_heartbeat"])
                    if (now - last_hb).total_seconds() > max_age_seconds:
                        await r.hdel(key, node_id)
                        removed += 1
                        logger.info("Removed stale node %s from %s", node_id, key)
                except Exception:
                    # Corrupt entry — remove it
                    await r.hdel(key, node_id)
                    removed += 1
        if cursor == "0" or cursor == 0:
            break
    return removed
