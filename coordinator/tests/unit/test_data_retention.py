"""
Unit tests for data retention — cleanup removes old records only,
monthly summary aggregation accuracy.
Task 7.12 — Design §24, Properties 14–15
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import models
from app.data_retention import run_data_retention, _get_thresholds


def _add_ledger(db, node_id, stream_id, days_ago, bytes_transferred=1_000_000, verified=True):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    entry = models.BandwidthLedger(
        session_id=stream_id,
        reporting_node_id=node_id,
        bytes_transferred=bytes_transferred,
        report_timestamp=ts,
        start_interval=ts - timedelta(minutes=60),
        end_interval=ts,
        is_verified=verified,
        trust_score=Decimal("0.90"),
    )
    db.add(entry)
    db.flush()
    return entry


def _add_probe(db, node_id, stream_id, days_ago):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    probe = models.ProbeResult(
        stream_id=stream_id,
        node_id=node_id,
        probe_type="stats_poll",
        success=True,
        probe_timestamp=ts,
    )
    db.add(probe)
    db.flush()
    return probe


class TestGetThresholds:
    def test_defaults(self):
        with patch.dict("os.environ", {}, clear=False):
            bw, pr = _get_thresholds()
        assert bw == 90
        assert pr == 60

    def test_custom_env(self):
        with patch.dict("os.environ", {
            "DATA_RETENTION_BANDWIDTH_DAYS": "30",
            "DATA_RETENTION_PROBES_DAYS": "14",
        }):
            bw, pr = _get_thresholds()
        assert bw == 30
        assert pr == 14


class TestBandwidthDeletion:
    def test_old_records_deleted(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="dr-u1")
        make_stream(stream_id="dr-s1", owner_user_id="dr-u1")
        make_node(node_id="dr-n1", stream_id="dr-s1", user_id="dr-u1")

        # Old record (100 days ago) — should be deleted with default 90-day threshold
        _add_ledger(test_db, "dr-n1", "dr-s1", days_ago=100)
        # Recent record (10 days ago) — should survive
        _add_ledger(test_db, "dr-n1", "dr-s1", days_ago=10)

        result = run_data_retention(test_db)
        assert result["bandwidth_deleted"] == 1

        remaining = test_db.query(models.BandwidthLedger).all()
        assert len(remaining) == 1

    def test_recent_records_preserved(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="dr-u2")
        make_stream(stream_id="dr-s2", owner_user_id="dr-u2")
        make_node(node_id="dr-n2", stream_id="dr-s2", user_id="dr-u2")

        _add_ledger(test_db, "dr-n2", "dr-s2", days_ago=5)
        _add_ledger(test_db, "dr-n2", "dr-s2", days_ago=30)

        result = run_data_retention(test_db)
        assert result["bandwidth_deleted"] == 0


class TestProbeDeletion:
    def test_old_probes_deleted(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="dr-u3")
        make_stream(stream_id="dr-s3", owner_user_id="dr-u3")
        make_node(node_id="dr-n3", stream_id="dr-s3", user_id="dr-u3")

        _add_probe(test_db, "dr-n3", "dr-s3", days_ago=70)  # older than 60-day default
        _add_probe(test_db, "dr-n3", "dr-s3", days_ago=10)  # recent

        result = run_data_retention(test_db)
        assert result["probes_deleted"] == 1

        remaining = test_db.query(models.ProbeResult).all()
        assert len(remaining) == 1

    def test_recent_probes_preserved(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="dr-u4")
        make_stream(stream_id="dr-s4", owner_user_id="dr-u4")
        make_node(node_id="dr-n4", stream_id="dr-s4", user_id="dr-u4")

        _add_probe(test_db, "dr-n4", "dr-s4", days_ago=5)
        result = run_data_retention(test_db)
        assert result["probes_deleted"] == 0


class TestAggregation:
    def test_aggregates_old_bandwidth_into_monthly(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="dr-u5")
        make_stream(stream_id="dr-s5", owner_user_id="dr-u5")
        make_node(node_id="dr-n5", stream_id="dr-s5", user_id="dr-u5")

        # Add several old records in the same month
        for _ in range(5):
            _add_ledger(test_db, "dr-n5", "dr-s5", days_ago=100, bytes_transferred=2_000_000)

        result = run_data_retention(test_db)
        assert result["aggregated"] >= 1

        summaries = test_db.query(models.MonthlySummary).filter_by(node_id="dr-n5").all()
        assert len(summaries) >= 1
        total = sum(s.total_bytes for s in summaries)
        assert total == 10_000_000  # 5 * 2MB

    def test_no_aggregation_for_recent_only(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="dr-u6")
        make_stream(stream_id="dr-s6", owner_user_id="dr-u6")
        make_node(node_id="dr-n6", stream_id="dr-s6", user_id="dr-u6")

        _add_ledger(test_db, "dr-n6", "dr-s6", days_ago=5)
        result = run_data_retention(test_db)
        assert result["aggregated"] == 0


class TestFullCycle:
    def test_empty_database_no_errors(self, test_db):
        result = run_data_retention(test_db)
        assert result["aggregated"] == 0
        assert result["bandwidth_deleted"] == 0
        assert result["probes_deleted"] == 0
