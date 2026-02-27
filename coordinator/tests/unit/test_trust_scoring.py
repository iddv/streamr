"""
Unit tests for trust scoring — verification logic, rolling 30-day window,
default score for new nodes, consequences (flagging, penalty).
Task 7.8 — Req 21.3, Design §24, Properties 32–34
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app import models
from app.trust_scoring import (
    apply_trust_consequences,
    calculate_trust_score,
    recalculate_and_store,
)


def _add_ledger(db, node_id, stream_id, verified, days_ago=0):
    """Insert a bandwidth ledger entry for trust score testing."""
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    entry = models.BandwidthLedger(
        session_id=stream_id,
        reporting_node_id=node_id,
        bytes_transferred=1_000_000,
        report_timestamp=ts,
        start_interval=ts - timedelta(minutes=60),
        end_interval=ts,
        is_verified=verified,
    )
    db.add(entry)
    db.flush()
    return entry


class TestCalculateTrustScore:
    def test_default_score_for_few_reports(self, test_db, make_user, make_stream, make_node):
        """Nodes with < 5 reports get default 0.75."""
        make_user(user_id="ts-u1")
        make_stream(stream_id="ts-s1", owner_user_id="ts-u1")
        make_node(node_id="ts-n1", stream_id="ts-s1", user_id="ts-u1")
        # Add only 3 reports
        for _ in range(3):
            _add_ledger(test_db, "ts-n1", "ts-s1", verified=True)

        score = calculate_trust_score("ts-n1", test_db)
        assert score == Decimal("0.75")


    def test_all_verified_gives_1(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="ts-u2")
        make_stream(stream_id="ts-s2", owner_user_id="ts-u2")
        make_node(node_id="ts-n2", stream_id="ts-s2", user_id="ts-u2")
        for _ in range(10):
            _add_ledger(test_db, "ts-n2", "ts-s2", verified=True)

        score = calculate_trust_score("ts-n2", test_db)
        assert score == Decimal("1.00")

    def test_half_verified_gives_half(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="ts-u3")
        make_stream(stream_id="ts-s3", owner_user_id="ts-u3")
        make_node(node_id="ts-n3", stream_id="ts-s3", user_id="ts-u3")
        for _ in range(5):
            _add_ledger(test_db, "ts-n3", "ts-s3", verified=True)
        for _ in range(5):
            _add_ledger(test_db, "ts-n3", "ts-s3", verified=False)

        score = calculate_trust_score("ts-n3", test_db)
        assert score == Decimal("0.50")

    def test_old_reports_excluded(self, test_db, make_user, make_stream, make_node):
        """Reports older than 30 days should not count."""
        make_user(user_id="ts-u4")
        make_stream(stream_id="ts-s4", owner_user_id="ts-u4")
        make_node(node_id="ts-n4", stream_id="ts-s4", user_id="ts-u4")
        # 10 old failed reports (35 days ago)
        for _ in range(10):
            _add_ledger(test_db, "ts-n4", "ts-s4", verified=False, days_ago=35)
        # 6 recent verified reports
        for _ in range(6):
            _add_ledger(test_db, "ts-n4", "ts-s4", verified=True, days_ago=1)

        score = calculate_trust_score("ts-n4", test_db)
        assert score == Decimal("1.00")

    def test_no_reports_returns_default(self, test_db):
        score = calculate_trust_score("nonexistent-node", test_db)
        assert score == Decimal("0.75")


class TestRecalculateAndStore:
    def test_stores_score_on_account(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="rcs-u1")
        make_stream(stream_id="rcs-s1", owner_user_id="rcs-u1")
        make_node(node_id="rcs-u1", stream_id="rcs-s1", user_id="rcs-u1")
        for _ in range(10):
            _add_ledger(test_db, "rcs-u1", "rcs-s1", verified=True)

        score = recalculate_and_store("rcs-u1", test_db)
        assert score == Decimal("1.00")

        account = test_db.query(models.UserAccount).filter_by(user_id="rcs-u1").first()
        assert account.trust_score == Decimal("1.00")


class TestApplyTrustConsequences:
    def test_flag_node_below_03(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="flag-u1")
        make_stream(stream_id="flag-s1", owner_user_id="flag-u1")
        node = make_node(node_id="flag-n1", stream_id="flag-s1", user_id="flag-u1")
        assert node.status == "active"

        apply_trust_consequences("flag-n1", Decimal("0.20"), test_db)
        test_db.flush()

        refreshed = test_db.query(models.Node).filter_by(node_id="flag-n1").first()
        assert refreshed.status == "flagged"

    def test_no_flag_above_03(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="noflag-u1")
        make_stream(stream_id="noflag-s1", owner_user_id="noflag-u1")
        make_node(node_id="noflag-n1", stream_id="noflag-s1", user_id="noflag-u1")

        apply_trust_consequences("noflag-n1", Decimal("0.60"), test_db)
        test_db.flush()

        node = test_db.query(models.Node).filter_by(node_id="noflag-n1").first()
        assert node.status == "active"

    def test_already_flagged_stays_flagged(self, test_db, make_user, make_stream, make_node):
        make_user(user_id="af-u1")
        make_stream(stream_id="af-s1", owner_user_id="af-u1")
        node = make_node(node_id="af-n1", stream_id="af-s1", user_id="af-u1")
        node.status = "flagged"
        test_db.flush()

        apply_trust_consequences("af-n1", Decimal("0.10"), test_db)
        test_db.flush()

        refreshed = test_db.query(models.Node).filter_by(node_id="af-n1").first()
        assert refreshed.status == "flagged"
