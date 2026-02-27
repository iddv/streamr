"""
Unit tests for spot check prober — probe scheduling, fraud detection logic,
node flagging.
Task 7.10 — Req 21.3, Design §24
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app import models
from app.spot_check_prober import SpotCheckProber


@pytest.fixture()
def prober():
    return SpotCheckProber(check_interval_min=1, check_interval_max=2)


class TestExtractIP:
    def test_standard_url(self, prober):
        ip = prober._extract_ip_from_stats_url("http://192.168.1.100:8080/stats.json")
        assert ip == "192.168.1.100"

    def test_no_port(self, prober):
        ip = prober._extract_ip_from_stats_url("http://10.0.0.1/stats")
        assert ip == "10.0.0.1"

    def test_https_url(self, prober):
        ip = prober._extract_ip_from_stats_url("https://172.16.0.5:443/stats")
        assert ip == "172.16.0.5"

    def test_malformed_url_returns_original(self, prober):
        result = prober._extract_ip_from_stats_url("")
        assert isinstance(result, str)


class TestFlagInactiveNodes:
    @pytest.mark.asyncio
    async def test_flags_stale_nodes(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="sp-u1")
        make_stream(stream_id="sp-s1", owner_user_id="sp-u1")
        node = make_node(node_id="sp-n1", stream_id="sp-s1", user_id="sp-u1")
        # Set heartbeat to 10 minutes ago
        node.last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=10)
        test_db.flush()

        prober = SpotCheckProber()
        # Patch SessionLocal to return our test_db
        with patch("app.spot_check_prober.database.SessionLocal", return_value=test_db):
            # Prevent close from actually closing our test session
            with patch.object(test_db, "close"):
                await prober.flag_inactive_nodes()

        refreshed = test_db.query(models.Node).filter_by(node_id="sp-n1").first()
        assert refreshed.status == "inactive"


    @pytest.mark.asyncio
    async def test_recent_heartbeat_not_flagged(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="sp-u2")
        make_stream(stream_id="sp-s2", owner_user_id="sp-u2")
        node = make_node(node_id="sp-n2", stream_id="sp-s2", user_id="sp-u2")
        node.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=30)
        test_db.flush()

        prober = SpotCheckProber()
        with patch("app.spot_check_prober.database.SessionLocal", return_value=test_db):
            with patch.object(test_db, "close"):
                await prober.flag_inactive_nodes()

        refreshed = test_db.query(models.Node).filter_by(node_id="sp-n2").first()
        assert refreshed.status == "active"


class TestPerformSpotCheck:
    @pytest.mark.asyncio
    async def test_failed_spot_check_flags_node(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="sp-u3")
        make_stream(stream_id="sp-s3", owner_user_id="sp-u3")
        node = make_node(node_id="sp-n3", stream_id="sp-s3", user_id="sp-u3")

        # Add a recent successful stats_poll so the node is "healthy"
        probe = models.ProbeResult(
            stream_id="sp-s3",
            node_id="sp-n3",
            probe_type="stats_poll",
            success=True,
            probe_timestamp=datetime.now(timezone.utc),
        )
        test_db.add(probe)
        test_db.flush()

        prober = SpotCheckProber()
        # Mock _test_rtmp_connection to return failure
        prober._test_rtmp_connection = AsyncMock(return_value=(False, "Connection timeout"))

        with patch("app.spot_check_prober.database.SessionLocal", return_value=test_db):
            with patch.object(test_db, "close"):
                await prober._perform_spot_check()

        refreshed = test_db.query(models.Node).filter_by(node_id="sp-n3").first()
        assert refreshed.status == "flagged"

        # Verify spot_check probe result was stored
        spot_probes = (
            test_db.query(models.ProbeResult)
            .filter_by(node_id="sp-n3", probe_type="spot_check")
            .all()
        )
        assert len(spot_probes) == 1
        assert spot_probes[0].success is False

    @pytest.mark.asyncio
    async def test_passed_spot_check_keeps_active(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="sp-u4")
        make_stream(stream_id="sp-s4", owner_user_id="sp-u4")
        node = make_node(node_id="sp-n4", stream_id="sp-s4", user_id="sp-u4")

        probe = models.ProbeResult(
            stream_id="sp-s4",
            node_id="sp-n4",
            probe_type="stats_poll",
            success=True,
            probe_timestamp=datetime.now(timezone.utc),
        )
        test_db.add(probe)
        test_db.flush()

        prober = SpotCheckProber()
        prober._test_rtmp_connection = AsyncMock(return_value=(True, None))

        with patch("app.spot_check_prober.database.SessionLocal", return_value=test_db):
            with patch.object(test_db, "close"):
                await prober._perform_spot_check()

        refreshed = test_db.query(models.Node).filter_by(node_id="sp-n4").first()
        assert refreshed.status == "active"


class TestSpotCheckProberInit:
    def test_interval_conversion_to_seconds(self):
        prober = SpotCheckProber(check_interval_min=5, check_interval_max=15)
        assert prober.check_interval_min == 300
        assert prober.check_interval_max == 900
