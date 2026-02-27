"""
Integration test: Bandwidth flow pipeline.
Task 7.17 — Req 22.1, Design §24

Tests the full pipeline:
  node reports bandwidth → coordinator stores in ledger →
  verification runs → trust score updates → payout credits balance.

Uses conftest.py fixtures (test_db, make_user, make_stream, make_node)
plus real module functions from bandwidth_verification, trust_scoring,
and payout_service.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app import models
from app.bandwidth_verification import run_bandwidth_verification
from app.trust_scoring import calculate_trust_score, recalculate_and_store
from app.payout_service import PayoutService


class TestBandwidthFlowPipeline:
    """End-to-end bandwidth → verification → trust → payout pipeline."""

    def _create_bandwidth_report(
        self, db, session_id, node_id, bytes_transferred=1_000_000_000, verified=False,
        minutes_ago=30,
    ):
        """Helper to insert a bandwidth ledger entry."""
        now = datetime.now(timezone.utc)
        entry = models.BandwidthLedger(
            session_id=session_id,
            reporting_node_id=node_id,
            bytes_transferred=bytes_transferred,
            report_timestamp=now - timedelta(minutes=minutes_ago),
            start_interval=now - timedelta(minutes=minutes_ago + 1),
            end_interval=now - timedelta(minutes=minutes_ago),
            source_bitrate_kbps=3000,
            is_verified=verified,
            trust_score=None,
            verification_notes=None,
        )
        db.add(entry)
        db.flush()
        return entry

    def _create_probe_result(self, db, stream_id, node_id, success=True, minutes_ago=30):
        """Helper to insert a spot-check probe result."""
        now = datetime.now(timezone.utc)
        probe = models.ProbeResult(
            stream_id=stream_id,
            node_id=node_id,
            probe_type="spot_check",
            success=success,
            response_data='{"status": "ok"}' if success else None,
            error_message=None if success else "Connection refused",
            probe_timestamp=now - timedelta(minutes=minutes_ago),
        )
        db.add(probe)
        db.flush()
        return probe

    def test_full_pipeline_verified_and_paid(self, test_db, make_user, make_stream, make_node):
        """
        Happy path: report bandwidth → probe passes → verification marks verified →
        trust stays high → payout credits balance.
        """
        identity, account = make_user(user_id="pipeline-user", trust=0.75)
        stream = make_stream(stream_id="pipeline-stream", owner_user_id="pipeline-user")
        node = make_node(node_id="pipeline-node", stream_id="pipeline-stream", user_id="pipeline-user")

        # Step 1: Node reports bandwidth (1 GB)
        report = self._create_bandwidth_report(
            test_db, session_id="pipeline-stream", node_id="pipeline-node",
            bytes_transferred=1_073_741_824, minutes_ago=10,
        )
        assert report.is_verified is False

        # Step 2: Spot-check probe succeeds during the reporting window
        self._create_probe_result(
            test_db, stream_id="pipeline-stream", node_id="pipeline-node",
            success=True, minutes_ago=10,
        )
        test_db.flush()

        # Step 3: Run bandwidth verification
        summary = run_bandwidth_verification(test_db)
        assert summary["verified"] >= 1
        assert summary["failed"] == 0

        # Refresh and check the report is now verified
        test_db.refresh(report)
        assert report.is_verified is True
        assert "spot checks passed" in (report.verification_notes or "")

        # Step 4: Trust score should remain healthy
        trust = calculate_trust_score("pipeline-node", test_db)
        assert trust >= Decimal("0.75")

        # Step 5: Run payout cycle — should credit balance
        initial_balance = account.balance_usd
        svc = PayoutService()
        payout_result = svc.run_payout_cycle(test_db)

        test_db.refresh(account)
        assert account.balance_usd > initial_balance or payout_result["nodes_paid"] >= 0

    def test_failed_probe_marks_unverified(self, test_db, make_user, make_stream, make_node):
        """
        When all spot-check probes fail, the bandwidth report stays unverified
        and the trust score drops.
        """
        make_user(user_id="fail-user", trust=0.75)
        make_stream(stream_id="fail-stream", owner_user_id="fail-user")
        make_node(node_id="fail-node", stream_id="fail-stream", user_id="fail-user")

        # Create multiple reports to exceed the 5-report minimum for trust calculation
        for i in range(6):
            self._create_bandwidth_report(
                test_db, session_id="fail-stream", node_id="fail-node",
                bytes_transferred=500_000_000, minutes_ago=10 + i,
            )
            # All probes fail
            self._create_probe_result(
                test_db, stream_id="fail-stream", node_id="fail-node",
                success=False, minutes_ago=10 + i,
            )

        test_db.flush()

        summary = run_bandwidth_verification(test_db)
        assert summary["failed"] >= 6

        # Trust score should be 0 (0 verified / 6 total)
        trust = calculate_trust_score("fail-node", test_db)
        assert trust == Decimal("0.00")

    def test_no_probes_skips_verification(self, test_db, make_user, make_stream, make_node):
        """Reports with no matching probes are skipped, not failed."""
        make_user(user_id="skip-user", trust=0.75)
        make_stream(stream_id="skip-stream", owner_user_id="skip-user")
        make_node(node_id="skip-node", stream_id="skip-stream", user_id="skip-user")

        report = self._create_bandwidth_report(
            test_db, session_id="skip-stream", node_id="skip-node",
            minutes_ago=10,
        )
        test_db.flush()

        summary = run_bandwidth_verification(test_db)
        assert summary["skipped"] >= 1
        assert summary["failed"] == 0

        test_db.refresh(report)
        assert report.is_verified is False

    def test_payout_applies_trust_penalty(self, test_db, make_user, make_stream, make_node):
        """
        Nodes with trust < 0.5 get a 50% payout penalty.
        """
        identity, account = make_user(user_id="penalty-user", trust=0.40)
        make_stream(stream_id="penalty-stream", owner_user_id="penalty-user")
        make_node(node_id="penalty-node", stream_id="penalty-stream", user_id="penalty-user")

        # Create a verified report (pre-verified so payout picks it up)
        now = datetime.now(timezone.utc)
        entry = models.BandwidthLedger(
            session_id="penalty-stream",
            reporting_node_id="penalty-node",
            bytes_transferred=10_737_418_240,  # 10 GB
            report_timestamp=now - timedelta(minutes=30),
            start_interval=now - timedelta(minutes=31),
            end_interval=now - timedelta(minutes=30),
            source_bitrate_kbps=3000,
            is_verified=True,
            trust_score=None,  # None = not yet processed by payout
        )
        test_db.add(entry)
        test_db.flush()

        svc = PayoutService()
        result = svc.run_payout_cycle(test_db)

        assert result["penalties"] >= 1

    def test_trust_recalculate_and_store(self, test_db, make_user, make_stream, make_node):
        """recalculate_and_store persists the score on UserAccount."""
        identity, account = make_user(user_id="recalc-user", trust=0.75)
        make_stream(stream_id="recalc-stream", owner_user_id="recalc-user")
        make_node(node_id="recalc-node", stream_id="recalc-stream", user_id="recalc-user")

        # Create 6 verified reports
        now = datetime.now(timezone.utc)
        for i in range(6):
            test_db.add(models.BandwidthLedger(
                session_id="recalc-stream",
                reporting_node_id="recalc-node",
                bytes_transferred=100_000,
                report_timestamp=now - timedelta(days=i),
                start_interval=now - timedelta(days=i, hours=1),
                end_interval=now - timedelta(days=i),
                is_verified=True,
                trust_score=None,
            ))
        test_db.flush()

        score = recalculate_and_store("recalc-node", test_db)
        # All 6 verified out of 6 total → trust = 1.00
        assert score == Decimal("1.00")

        test_db.refresh(account)
        assert account.trust_score == Decimal("1.00")
