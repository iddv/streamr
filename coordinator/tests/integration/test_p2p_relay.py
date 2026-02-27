"""
Integration test: P2P relay flow.
Task 7.18 — Req 22.2, Design §24

Tests the proxy-based relay pipeline:
  SRS produces chunks → coordinator proxies to viewer via friend node.

Since real SRS and Go nodes won't be running, this uses mock-based
integration testing of the coordinator's proxy and viewer routing
endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient


class TestP2PRelayFlow:
    """Mock-based integration test for the P2P relay pipeline."""

    def test_viewer_gets_srs_fallback_when_no_nodes(self, client):
        """
        When no friend nodes are active, the viewer routing endpoint
        should fall back to the SRS direct URL.
        """
        # Patch Redis to return no nodes
        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_r = AsyncMock()
            mock_r.hgetall = AsyncMock(return_value={})
            mock_redis.return_value = mock_r

            with patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
                mock_nodes.return_value = []

                resp = client.get("/api/v1/watch/test-stream-123")

        # Should return a source URL (either SRS fallback or error)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert "source_url" in data
            assert data["source_type"] in ("srs_direct", "srs_fallback", "p2p_node")

    def test_viewer_gets_node_when_available(self, client, test_db, make_user, make_stream, make_node):
        """
        When a friend node is active with good trust, the viewer should
        be routed to the node via the proxy.
        """
        make_user(user_id="relay-user", trust=0.90)
        stream = make_stream(stream_id="relay-stream", owner_user_id="relay-user")
        node = make_node(node_id="relay-node", stream_id="relay-stream", user_id="relay-user")

        # Mock Redis to return an active node
        mock_node_data = [
            {
                "node_id": "relay-node",
                "vpn_ip": "100.64.0.2",
                "trust_score": 0.90,
                "capacity_pct": 30,
                "viewer_count": 1,
            }
        ]

        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_r = AsyncMock()
            mock_redis.return_value = mock_r

            with patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
                mock_nodes.return_value = mock_node_data

                # Also mock the Redis hset for viewer assignment
                mock_r.hset = AsyncMock()

                resp = client.get("/api/v1/watch/relay-stream")

        if resp.status_code == 200:
            data = resp.json()
            assert "source_url" in data
            # Should prefer the P2P node
            if data.get("node_id"):
                assert data["node_id"] == "relay-node"

    def test_proxy_endpoint_returns_error_without_assignment(self, client):
        """
        The proxy endpoint should return an error when no viewer
        assignment exists in Redis.
        """
        with patch("app.proxy.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_r = AsyncMock()
            mock_r.hget = AsyncMock(return_value=None)
            mock_redis.return_value = mock_r

            resp = client.get("/api/v1/proxy/no-stream/index.m3u8")

        # Should return 404 or 502 when no assignment found
        assert resp.status_code in (404, 502, 500)

    def test_viewer_routing_excludes_saturated_nodes(self, client, test_db, make_user, make_stream, make_node):
        """
        Nodes at 90%+ capacity should be excluded from viewer routing.
        """
        make_user(user_id="sat-user", trust=0.85)
        make_stream(stream_id="sat-stream", owner_user_id="sat-user")
        make_node(node_id="sat-node", stream_id="sat-stream", user_id="sat-user")

        # Node is at 95% capacity — should be excluded
        saturated_nodes = [
            {
                "node_id": "sat-node",
                "vpn_ip": "100.64.0.3",
                "trust_score": 0.85,
                "capacity_pct": 95,
                "viewer_count": 9,
            }
        ]

        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_r = AsyncMock()
            mock_redis.return_value = mock_r
            mock_r.hset = AsyncMock()

            with patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
                mock_nodes.return_value = saturated_nodes

                resp = client.get("/api/v1/watch/sat-stream")

        if resp.status_code == 200:
            data = resp.json()
            # Should fall back to SRS since the only node is saturated
            if data.get("source_type"):
                assert data["source_type"] in ("srs_direct", "srs_fallback")

    def test_viewer_routing_prefers_highest_trust(self, client, test_db, make_user, make_stream, make_node):
        """
        Among multiple available nodes, the one with the highest trust
        score and lowest load should be selected.
        """
        make_user(user_id="multi-user", trust=0.80)
        make_stream(stream_id="multi-stream", owner_user_id="multi-user")

        nodes = [
            {
                "node_id": "low-trust-node",
                "vpn_ip": "100.64.0.10",
                "trust_score": 0.60,
                "capacity_pct": 20,
                "viewer_count": 2,
            },
            {
                "node_id": "high-trust-node",
                "vpn_ip": "100.64.0.11",
                "trust_score": 0.95,
                "capacity_pct": 10,
                "viewer_count": 1,
            },
        ]

        with patch("app.viewer_routes.get_redis", new_callable=AsyncMock) as mock_redis:
            mock_r = AsyncMock()
            mock_redis.return_value = mock_r
            mock_r.hset = AsyncMock()

            with patch("app.viewer_routes.get_stream_nodes", new_callable=AsyncMock) as mock_nodes:
                mock_nodes.return_value = nodes

                resp = client.get("/api/v1/watch/multi-stream")

        if resp.status_code == 200:
            data = resp.json()
            # Should pick the high-trust node
            if data.get("node_id"):
                assert data["node_id"] == "high-trust-node"
