"""
Unit tests for stats collector — heartbeat timeout detection,
node status transitions, error handling for unreachable nodes.
Task 7.9 — Req 21.2, Design §24
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.stats_collector import StatsCollector


@pytest.fixture()
def collector():
    return StatsCollector(poll_interval=10)


class TestValidateStatsData:
    def test_valid_stats_with_active_stream(self, collector):
        data = {
            "streams": [
                {
                    "stream_name": "live/test-stream",
                    "connections": [{"state": "publishing"}],
                }
            ]
        }
        assert collector._validate_stats_data(data, "test-stream") is True

    def test_no_streams_returns_false(self, collector):
        assert collector._validate_stats_data({"streams": []}, "s1") is False

    def test_empty_connections_returns_false(self, collector):
        data = {"streams": [{"stream_name": "live/s1", "connections": []}]}
        assert collector._validate_stats_data(data, "s1") is False

    def test_wrong_stream_id_returns_false(self, collector):
        data = {
            "streams": [
                {
                    "stream_name": "live/other-stream",
                    "connections": [{"state": "publishing"}],
                }
            ]
        }
        assert collector._validate_stats_data(data, "my-stream") is False

    def test_unhealthy_state_returns_false(self, collector):
        data = {
            "streams": [
                {
                    "stream_name": "live/s1",
                    "connections": [{"state": "disconnected"}],
                }
            ]
        }
        assert collector._validate_stats_data(data, "s1") is False


    def test_streaming_state_is_valid(self, collector):
        data = {
            "streams": [
                {
                    "stream_name": "live/s1",
                    "connections": [{"state": "streaming"}],
                }
            ]
        }
        assert collector._validate_stats_data(data, "s1") is True

    def test_connected_state_is_valid(self, collector):
        data = {
            "streams": [
                {
                    "stream_name": "live/s1",
                    "connections": [{"state": "Connected"}],
                }
            ]
        }
        assert collector._validate_stats_data(data, "s1") is True

    def test_malformed_data_returns_false(self, collector):
        assert collector._validate_stats_data(None, "s1") is False

    def test_multiple_streams_finds_match(self, collector):
        data = {
            "streams": [
                {"stream_name": "live/other", "connections": []},
                {
                    "stream_name": "live/target",
                    "connections": [{"state": "publishing"}],
                },
            ]
        }
        assert collector._validate_stats_data(data, "target") is True


class TestCollectNodeStats:
    @pytest.mark.asyncio
    async def test_successful_collection(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="sc-u1")
        make_stream(stream_id="sc-s1", owner_user_id="sc-u1")
        node = make_node(node_id="sc-n1", stream_id="sc-s1", user_id="sc-u1")

        collector = StatsCollector()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "streams": [
                {
                    "stream_name": "live/sc-s1",
                    "connections": [{"state": "publishing"}],
                }
            ]
        }
        collector.client = AsyncMock()
        collector.client.get = AsyncMock(return_value=mock_response)

        await collector._collect_node_stats(node, test_db)

        from app.models import ProbeResult
        probes = test_db.query(ProbeResult).filter_by(node_id="sc-n1").all()
        assert len(probes) == 1
        assert probes[0].success is True

    @pytest.mark.asyncio
    async def test_http_error_stores_failure(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="sc-u2")
        make_stream(stream_id="sc-s2", owner_user_id="sc-u2")
        node = make_node(node_id="sc-n2", stream_id="sc-s2", user_id="sc-u2")

        collector = StatsCollector()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        collector.client = AsyncMock()
        collector.client.get = AsyncMock(return_value=mock_response)

        await collector._collect_node_stats(node, test_db)

        from app.models import ProbeResult
        probes = test_db.query(ProbeResult).filter_by(node_id="sc-n2").all()
        assert len(probes) == 1
        assert probes[0].success is False

    @pytest.mark.asyncio
    async def test_connection_error_stores_failure(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="sc-u3")
        make_stream(stream_id="sc-s3", owner_user_id="sc-u3")
        node = make_node(node_id="sc-n3", stream_id="sc-s3", user_id="sc-u3")

        collector = StatsCollector()
        collector.client = AsyncMock()
        collector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        await collector._collect_node_stats(node, test_db)

        from app.models import ProbeResult
        probes = test_db.query(ProbeResult).filter_by(node_id="sc-n3").all()
        assert len(probes) == 1
        assert probes[0].success is False
        assert "refused" in probes[0].error_message
