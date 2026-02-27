"""
Payout service — contribution-weighted distribution from verified bandwidth.
Task 5.5 — Req 15.1–15.6, Design §18

Calculates payouts from *verified* bandwidth reports, applies trust-score
penalties, credits UserAccount balances, and logs every cycle to payout_log /
payout_log_entries.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from . import models
from .economic_config import economic_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRUST_PENALTY_THRESHOLD = Decimal("0.5")
TRUST_PENALTY_MULTIPLIER = Decimal("0.5")  # 50% payout when trust < 0.5


def _gb_from_bytes(b: int) -> Decimal:
    return (Decimal(str(b)) / Decimal(str(1024 ** 3))).quantize(Decimal("0.0001"))


# ---------------------------------------------------------------------------
# Core payout cycle
# ---------------------------------------------------------------------------

class PayoutService:
    """Hourly payout cycle driven by verified bandwidth reports."""

    def run_payout_cycle(self, db: Session) -> dict:
        """
        Execute one payout cycle:
        1. Gather verified-but-unpaid bandwidth reports from the last hour.
        2. Aggregate bytes per node.
        3. Calculate earnings using EconomicConfig rate, minus platform margin.
        4. Apply trust-score penalty where trust < 0.5.
        5. Credit UserAccount.balance_usd.
        6. Log to payout_log + payout_log_entries.
        7. Mark processed reports (set trust_score on ledger rows).

        Returns summary dict.
        """
        now = datetime.now(timezone.utc)
        cycle_start = now - timedelta(hours=1)

        # 1. Verified reports not yet paid (trust_score IS NULL on ledger = not yet processed by payout)
        reports = (
            db.query(models.BandwidthLedger)
            .filter(
                models.BandwidthLedger.is_verified == True,  # noqa: E712
                models.BandwidthLedger.trust_score.is_(None),
                models.BandwidthLedger.report_timestamp >= cycle_start,
            )
            .all()
        )

        if not reports:
            logger.info("Payout cycle: no verified unpaid reports")
            return {"nodes_paid": 0, "total_usd": "0.00", "penalties": 0}

        # 2. Aggregate bytes per node
        node_bytes: Dict[str, int] = {}
        node_user: Dict[str, str] = {}  # node_id → user_id (from ledger's reporting_node)
        for r in reports:
            node_bytes[r.reporting_node_id] = node_bytes.get(r.reporting_node_id, 0) + r.bytes_transferred
            # Resolve user_id from Node table (first match)
            if r.reporting_node_id not in node_user:
                node = (
                    db.query(models.Node)
                    .filter(models.Node.node_id == r.reporting_node_id)
                    .first()
                )
                node_user[r.reporting_node_id] = node.user_id if node else r.reporting_node_id

        total_bytes = sum(node_bytes.values())
        if total_bytes == 0:
            logger.info("Payout cycle: total verified bytes = 0")
            return {"nodes_paid": 0, "total_usd": "0.00", "penalties": 0}

        # 3-4. Calculate per-node earnings
        rate = economic_config.rate_per_gb
        margin = economic_config.platform_margin
        min_threshold = economic_config.min_payout_threshold
        net_rate = rate * (Decimal("1") - margin)  # after platform cut

        entries: list[dict] = []
        total_amount = Decimal("0")
        penalties_applied = 0

        for node_id, nbytes in node_bytes.items():
            gb = _gb_from_bytes(nbytes)
            earnings = (gb * net_rate).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

            # Look up trust score
            user_id = node_user.get(node_id, node_id)
            account = db.query(models.UserAccount).filter(models.UserAccount.user_id == user_id).first()
            trust = Decimal(str(account.trust_score)) if account else Decimal("0.75")

            penalty = False
            if trust < TRUST_PENALTY_THRESHOLD:
                earnings = (earnings * TRUST_PENALTY_MULTIPLIER).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
                penalty = True
                penalties_applied += 1

            if earnings < min_threshold:
                # Below minimum — still log but don't credit
                entries.append({
                    "node_id": node_id,
                    "user_id": user_id,
                    "bytes": nbytes,
                    "earnings": Decimal("0"),
                    "trust": trust,
                    "penalty": penalty,
                })
                continue

            # 5. Credit balance
            if not account:
                account = models.UserAccount(
                    user_id=user_id,
                    balance_usd=Decimal("0"),
                    total_gb_relayed=Decimal("0"),
                    earnings_last_30d=Decimal("0"),
                    trust_score=trust,
                    flags=[],
                    last_updated_at=now,
                )
                db.add(account)
                db.flush()

            account.balance_usd += earnings
            account.total_gb_relayed += gb
            account.earnings_last_30d += earnings
            account.last_updated_at = now
            total_amount += earnings

            entries.append({
                "node_id": node_id,
                "user_id": user_id,
                "bytes": nbytes,
                "earnings": earnings,
                "trust": trust,
                "penalty": penalty,
            })

        # 6. Log cycle
        payout_log = models.PayoutLog(
            cycle_timestamp=now,
            total_amount_usd=total_amount,
            total_bytes_processed=total_bytes,
            nodes_paid=len([e for e in entries if e["earnings"] > 0]),
            penalties_applied=penalties_applied,
            notes=f"Rate {rate}/GB, margin {margin}, {len(reports)} reports processed",
        )
        db.add(payout_log)
        db.flush()  # get payout_log.id

        for e in entries:
            db.add(models.PayoutLogEntry(
                payout_log_id=payout_log.id,
                node_id=e["node_id"],
                user_id=e["user_id"],
                bytes_relayed=e["bytes"],
                earnings_usd=e["earnings"],
                trust_score=e["trust"],
                penalty_applied=e["penalty"],
                timestamp=now,
            ))

        # 7. Stamp processed reports so they aren't picked up again
        for r in reports:
            user_id = node_user.get(r.reporting_node_id, r.reporting_node_id)
            account = db.query(models.UserAccount).filter(models.UserAccount.user_id == user_id).first()
            r.trust_score = Decimal(str(account.trust_score)) if account else Decimal("0.75")

        db.commit()

        summary = {
            "nodes_paid": payout_log.nodes_paid,
            "total_usd": str(total_amount),
            "penalties": penalties_applied,
            "reports_processed": len(reports),
        }
        logger.info("Payout cycle complete: %s", summary)
        return summary

    # ------------------------------------------------------------------
    # Legacy helpers kept for backward-compat with existing endpoints
    # ------------------------------------------------------------------

    def calculate_payouts(self, db: Session, hours_back: int = 1) -> Dict:
        """Legacy payout preview (read-only, does not credit accounts)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        logs = (
            db.query(models.PayoutLog)
            .filter(models.PayoutLog.cycle_timestamp >= cutoff)
            .all()
        )
        result = {}
        for log in logs:
            result[str(log.id)] = {
                "cycle_timestamp": log.cycle_timestamp.isoformat(),
                "total_amount_usd": str(log.total_amount_usd),
                "total_bytes_processed": log.total_bytes_processed,
                "nodes_paid": log.nodes_paid,
                "penalties_applied": log.penalties_applied,
            }
        return result

    def get_node_earnings_summary(self, db: Session, node_id: str, days_back: int = 7) -> Dict:
        """Return earnings summary for a node over the given period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        entries = (
            db.query(models.PayoutLogEntry)
            .filter(
                models.PayoutLogEntry.node_id == node_id,
                models.PayoutLogEntry.timestamp >= cutoff,
            )
            .order_by(models.PayoutLogEntry.timestamp.desc())
            .all()
        )
        total = sum(e.earnings_usd for e in entries)
        return {
            "node_id": node_id,
            "period": f"Last {days_back} days",
            "total_estimated_earnings": float(total),
            "entries": len(entries),
        }

    def get_leaderboard(self, db: Session, limit: int = 10) -> List[Dict]:
        """Top nodes by 30-day earnings."""
        accounts = (
            db.query(models.UserAccount)
            .filter(models.UserAccount.earnings_last_30d > 0)
            .order_by(models.UserAccount.earnings_last_30d.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "node_id": a.user_id[:8] + "...",
                "earnings_30d": float(a.earnings_last_30d),
                "gb_relayed": float(a.total_gb_relayed),
                "trust_score": float(a.trust_score),
            }
            for a in accounts
        ]
