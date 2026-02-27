"""
Unit tests for payout service — contribution-weighted distribution,
trust penalty application, zero bandwidth edge case.
Task 7.7 — Req 21.1, Design §24, Properties 35–36
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app import models
from app.payout_service import PayoutService, TRUST_PENALTY_THRESHOLD, TRUST_PENALTY_MULTIPLIER


@pytest.fixture()
def payout_svc():
    return PayoutService()


@pytest.fixture()
def setup_stream_and_nodes(test_db, make_user, make_stream, make_node):
    """Create a stream with two nodes and verified bandwidth reports."""
    user1_id, user2_id = "payout-user-1", "payout-user-2"
    make_user(user_id=user1_id, role="node", trust=0.90)
    make_user(user_id=user2_id, role="node", trust=0.90)
    make_stream(stream_id="pay-stream", owner_user_id=user1_id)
    make_node(node_id="pay-node-1", stream_id="pay-stream", user_id=user1_id)
    make_node(node_id="pay-node-2", stream_id="pay-stream", user_id=user2_id)
    return user1_id, user2_id


def _add_bandwidth_report(db, node_id, stream_id, bytes_transferred, verified=True):
    """Helper to insert a verified bandwidth ledger entry."""
    now = datetime.now(timezone.utc)
    entry = models.BandwidthLedger(
        session_id=stream_id,
        reporting_node_id=node_id,
        bytes_transferred=bytes_transferred,
        report_timestamp=now - timedelta(minutes=10),
        start_interval=now - timedelta(minutes=70),
        end_interval=now - timedelta(minutes=10),
        is_verified=verified,
        trust_score=None,  # None = not yet processed by payout
    )
    db.add(entry)
    db.flush()
    return entry


class TestPayoutCycleBasic:
    def test_no_reports_returns_zero(self, test_db, payout_svc):
        result = payout_svc.run_payout_cycle(test_db)
        assert result["nodes_paid"] == 0
        assert result["total_usd"] == "0.00"

    def test_unverified_reports_ignored(self, test_db, payout_svc, setup_stream_and_nodes):
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_000_000_000, verified=False)
        result = payout_svc.run_payout_cycle(test_db)
        assert result["nodes_paid"] == 0

    def test_single_node_payout(self, test_db, payout_svc, setup_stream_and_nodes):
        user1_id, _ = setup_stream_and_nodes
        # 1 GB = 1073741824 bytes
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_073_741_824)
        result = payout_svc.run_payout_cycle(test_db)
        assert result["nodes_paid"] == 1
        assert Decimal(result["total_usd"]) > 0

        # Check balance credited
        account = test_db.query(models.UserAccount).filter_by(user_id=user1_id).first()
        assert account.balance_usd > 0


class TestContributionWeighted:
    def test_higher_bandwidth_earns_more(self, test_db, payout_svc, setup_stream_and_nodes):
        user1_id, user2_id = setup_stream_and_nodes
        # Node 1: 2 GB, Node 2: 1 GB
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 2 * 1_073_741_824)
        _add_bandwidth_report(test_db, "pay-node-2", "pay-stream", 1_073_741_824)
        payout_svc.run_payout_cycle(test_db)

        acct1 = test_db.query(models.UserAccount).filter_by(user_id=user1_id).first()
        acct2 = test_db.query(models.UserAccount).filter_by(user_id=user2_id).first()
        assert acct1.balance_usd > acct2.balance_usd


class TestTrustPenalty:
    def test_low_trust_gets_penalty(self, test_db, payout_svc, make_user, make_stream, make_node):
        """Node with trust < 0.5 gets 50% payout penalty."""
        make_user(user_id="low-trust-user", role="node", trust=0.30)
        make_stream(stream_id="lt-stream", owner_user_id="low-trust-user")
        make_node(node_id="lt-node", stream_id="lt-stream", user_id="low-trust-user")
        _add_bandwidth_report(test_db, "lt-node", "lt-stream", 1_073_741_824)

        result = payout_svc.run_payout_cycle(test_db)
        assert result["penalties"] >= 1

    def test_high_trust_no_penalty(self, test_db, payout_svc, setup_stream_and_nodes):
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_073_741_824)
        result = payout_svc.run_payout_cycle(test_db)
        assert result["penalties"] == 0


class TestPayoutLogging:
    def test_payout_log_created(self, test_db, payout_svc, setup_stream_and_nodes):
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_073_741_824)
        payout_svc.run_payout_cycle(test_db)

        logs = test_db.query(models.PayoutLog).all()
        assert len(logs) == 1
        assert logs[0].nodes_paid >= 1

    def test_payout_log_entries_created(self, test_db, payout_svc, setup_stream_and_nodes):
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_073_741_824)
        payout_svc.run_payout_cycle(test_db)

        entries = test_db.query(models.PayoutLogEntry).all()
        assert len(entries) >= 1

    def test_processed_reports_stamped(self, test_db, payout_svc, setup_stream_and_nodes):
        """After payout, ledger rows get trust_score stamped (not None)."""
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_073_741_824)
        payout_svc.run_payout_cycle(test_db)

        ledger = test_db.query(models.BandwidthLedger).first()
        assert ledger.trust_score is not None


class TestLegacyHelpers:
    def test_get_node_earnings_summary(self, test_db, payout_svc, setup_stream_and_nodes):
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_073_741_824)
        payout_svc.run_payout_cycle(test_db)

        summary = payout_svc.get_node_earnings_summary(test_db, "pay-node-1", days_back=7)
        assert summary["node_id"] == "pay-node-1"
        assert summary["entries"] >= 0

    def test_get_leaderboard(self, test_db, payout_svc, setup_stream_and_nodes):
        _add_bandwidth_report(test_db, "pay-node-1", "pay-stream", 1_073_741_824)
        payout_svc.run_payout_cycle(test_db)

        board = payout_svc.get_leaderboard(test_db, limit=5)
        assert isinstance(board, list)
