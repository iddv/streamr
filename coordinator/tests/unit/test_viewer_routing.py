"""
Unit tests for viewer routing — trust-based selection, SRS fallback,
capacity saturation exclusion, peer list ordering.
Task 7.11 — Req 21, Design §24, Properties 25–26, 30–31
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.viewer_routes import _pick_best_node, _log_fallback


# ---------------------------------------------------------------------------
# Helpers — mock Redis node data
# ---------------------------------------------------------------------------

def _node(node_id, trust=0.9, capacity=50, viewers=2):
    return {
        "node_id": node_id,
        "vpn_ip": f"10.0.0.{node_id[-1]}",
        "trust_score": trust,
        "capacity_pct": capacity,
        "viewer_count": viewers,
    }


# ---------------------------------------------------------------------------
# _pick_best_node
# ---------------------------------------------------------------------------


class TestPickBestNode:
    @pytest.mark.asyncio
    async def test_picks_highest_trust(self):
        nodes = [
            _node("n1", trust=0.7, capacity=30, viewers=1),
            _node("n2", trust=0.95, capacity=30, viewers=1),
            _node("n3", trust=0.8, capacity=30, viewers=1),
        ]
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock) as mock_redis, \
             patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
            mock_nodes.return_value = nodes
            best = await _pick_best_node("stream-1")
        assert best["node_id"] == "n2"

    @pytest.mark.asyncio
    async def test_breaks_tie_by_lowest_viewers(self):
        nodes = [
            _node("n1", trust=0.9, capacity=30, viewers=5),
            _node("n2", trust=0.9, capacity=30, viewers=1),
        ]
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock), \
             patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
            mock_nodes.return_value = nodes
            best = await _pick_best_node("stream-1")
        assert best["node_id"] == "n2"


    @pytest.mark.asyncio
    async def test_excludes_saturated_nodes(self):
        """Nodes with capacity_pct >= 90 should be excluded."""
        nodes = [
            _node("n1", trust=0.99, capacity=95, viewers=10),  # saturated
            _node("n2", trust=0.7, capacity=50, viewers=2),
        ]
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock), \
             patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
            mock_nodes.return_value = nodes
            best = await _pick_best_node("stream-1")
        assert best["node_id"] == "n2"

    @pytest.mark.asyncio
    async def test_excludes_low_trust_nodes(self):
        """Nodes with trust_score < 0.5 should be excluded."""
        nodes = [
            _node("n1", trust=0.3, capacity=10, viewers=0),  # low trust
            _node("n2", trust=0.6, capacity=50, viewers=2),
        ]
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock), \
             patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
            mock_nodes.return_value = nodes
            best = await _pick_best_node("stream-1")
        assert best["node_id"] == "n2"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_saturated(self):
        nodes = [
            _node("n1", trust=0.9, capacity=95, viewers=10),
            _node("n2", trust=0.9, capacity=92, viewers=8),
        ]
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock), \
             patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
            mock_nodes.return_value = nodes
            best = await _pick_best_node("stream-1")
        assert best is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_nodes(self):
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock), \
             patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
            mock_nodes.return_value = []
            best = await _pick_best_node("stream-1")
        assert best is None

    @pytest.mark.asyncio
    async def test_returns_none_on_redis_error(self):
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_redis.side_effect = ConnectionError("Redis down")
            best = await _pick_best_node("stream-1")
        assert best is None

    @pytest.mark.asyncio
    async def test_all_low_trust_returns_none(self):
        nodes = [
            _node("n1", trust=0.2, capacity=10, viewers=0),
            _node("n2", trust=0.4, capacity=10, viewers=0),
        ]
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock), \
             patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
            mock_nodes.return_value = nodes
            best = await _pick_best_node("stream-1")
        assert best is None


# ---------------------------------------------------------------------------
# SRS fallback logging
# ---------------------------------------------------------------------------


class TestLogFallback:
    def test_log_fallback_does_not_raise(self):
        """Smoke test — _log_fallback should not throw."""
        _log_fallback("stream-1", "no_active_nodes")

    def test_log_fallback_various_reasons(self):
        for reason in ("no_active_nodes", "node_offline", "low_trust"):
            _log_fallback("s1", reason)  # should not raise


# ---------------------------------------------------------------------------
# watch_stream endpoint (via TestClient)
# ---------------------------------------------------------------------------


class TestWatchStreamEndpoint:
    @pytest.mark.asyncio
    async def test_returns_friend_node_when_available(self, client):
        node_data = _node("friend-1", trust=0.9, capacity=40, viewers=1)
        with patch("app.viewer_routes._pick_best_node", new_callable=AsyncMock) as mock_pick, \
             patch("app.viewer_routes._record_viewer_assignment", new_callable=AsyncMock):
            mock_pick.return_value = node_data
            resp = client.get("/api/v1/watch/test-stream")
        assert resp.status_code == 200
        body = resp.json()
        assert body["source_type"] == "friend_node"
        assert body["node_id"] == "friend-1"
        assert "proxy" in body["source_url"]

    @pytest.mark.asyncio
    async def test_falls_back_to_srs(self, client):
        with patch("app.viewer_routes._pick_best_node", new_callable=AsyncMock) as mock_pick:
            mock_pick.return_value = None
            resp = client.get("/api/v1/watch/test-stream")
        assert resp.status_code == 200
        body = resp.json()
        assert body["source_type"] == "srs"
        assert body["node_id"] is None
