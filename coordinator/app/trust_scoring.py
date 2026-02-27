"""
Trust score calculation and consequence enforcement.
Tasks 5.2, 5.3 — Req 13.4–13.10, Design §16
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models

logger = logging.getLogger(__name__)


def calculate_trust_score(node_id: str, db: Session) -> Decimal:
    """
    Trust score = verified_reports / total_reports over a rolling 30-day window.
    Returns 0.75 default for nodes with fewer than 5 reports.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    total = (
        db.query(func.count(models.BandwidthLedger.id))
        .filter(
            models.BandwidthLedger.reporting_node_id == node_id,
            models.BandwidthLedger.report_timestamp > cutoff,
        )
        .scalar()
    ) or 0

    if total < 5:
        return Decimal("0.75")

    verified = (
        db.query(func.count(models.BandwidthLedger.id))
        .filter(
            models.BandwidthLedger.reporting_node_id == node_id,
            models.BandwidthLedger.report_timestamp > cutoff,
            models.BandwidthLedger.is_verified == True,  # noqa: E712
        )
        .scalar()
    ) or 0

    score = Decimal(str(verified / total)).quantize(Decimal("0.01"))
    return score


def recalculate_and_store(node_id: str, db: Session) -> Decimal:
    """Recalculate trust score and persist it on the UserAccount row."""
    score = calculate_trust_score(node_id, db)

    account = (
        db.query(models.UserAccount)
        .filter(models.UserAccount.user_id == node_id)
        .first()
    )
    if account:
        account.trust_score = score
        account.last_updated_at = datetime.now(timezone.utc)

    return score


def apply_trust_consequences(node_id: str, trust_score: Decimal, db: Session) -> None:
    """
    Enforce consequences based on trust score thresholds.
    - < 0.3 → flag node, remove from viewer assignments
    - < 0.5 → payout penalty applied at payout time (not here)
    """
    if trust_score < Decimal("0.3"):
        flagged = (
            db.query(models.Node)
            .filter(
                models.Node.node_id == node_id,
                models.Node.status != "flagged",
            )
            .all()
        )
        for node in flagged:
            node.status = "flagged"
            logger.warning(
                "Node %s flagged — trust score %.2f below 0.3 threshold",
                node_id,
                trust_score,
            )
