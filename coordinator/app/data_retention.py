"""
Data Retention Background Task

Aggregates old bandwidth_ledger records into monthly_summaries,
then deletes stale bandwidth_ledger and probe_results entries.

Configurable via environment variables:
  DATA_RETENTION_BANDWIDTH_DAYS  (default 90)
  DATA_RETENTION_PROBES_DAYS     (default 60)

Scheduled daily at 03:00 UTC via APScheduler (see main.py).
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, literal, Date
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .models import BandwidthLedger, ProbeResult, MonthlySummary

logger = logging.getLogger(__name__)


def _get_thresholds() -> tuple[int, int]:
    """Read retention thresholds from env vars with defaults."""
    bandwidth_days = int(os.getenv("DATA_RETENTION_BANDWIDTH_DAYS", "90"))
    probes_days = int(os.getenv("DATA_RETENTION_PROBES_DAYS", "60"))
    return bandwidth_days, probes_days


def run_data_retention(db: Session) -> dict:
    """
    Execute the full data-retention cycle:
      1. Aggregate old bandwidth_ledger rows into monthly_summaries (upsert).
      2. Delete bandwidth_ledger rows older than threshold.
      3. Delete probe_results rows older than threshold.
      4. Log counts.

    Returns a dict with counts for observability / testing.
    """
    bandwidth_days, probes_days = _get_thresholds()
    now = datetime.now(timezone.utc)
    bandwidth_cutoff = now - timedelta(days=bandwidth_days)
    probes_cutoff = now - timedelta(days=probes_days)

    logger.info(
        "Data retention starting — bandwidth_cutoff=%s (%d days), probes_cutoff=%s (%d days)",
        bandwidth_cutoff.isoformat(),
        bandwidth_days,
        probes_cutoff.isoformat(),
        probes_days,
    )

    # ------------------------------------------------------------------
    # Step 1: Aggregate old bandwidth_ledger into monthly_summaries
    # ------------------------------------------------------------------
    aggregated_count = _aggregate_bandwidth(db, bandwidth_cutoff)

    # ------------------------------------------------------------------
    # Step 2: Delete old bandwidth_ledger entries
    # ------------------------------------------------------------------
    bandwidth_deleted = (
        db.query(BandwidthLedger)
        .filter(BandwidthLedger.report_timestamp < bandwidth_cutoff)
        .delete(synchronize_session="fetch")
    )

    # ------------------------------------------------------------------
    # Step 3: Delete old probe_results entries
    # ------------------------------------------------------------------
    probes_deleted = (
        db.query(ProbeResult)
        .filter(ProbeResult.probe_timestamp < probes_cutoff)
        .delete(synchronize_session="fetch")
    )

    db.commit()

    logger.info(
        "Data retention complete — aggregated=%d, bandwidth_deleted=%d, probes_deleted=%d",
        aggregated_count,
        bandwidth_deleted,
        probes_deleted,
    )

    return {
        "aggregated": aggregated_count,
        "bandwidth_deleted": bandwidth_deleted,
        "probes_deleted": probes_deleted,
    }


def _aggregate_bandwidth(db: Session, cutoff: datetime) -> int:
    """
    Group bandwidth_ledger rows older than *cutoff* by
    (reporting_node_id, month) and upsert into monthly_summaries.

    Returns the number of groups (rows upserted).
    """
    # Build the aggregation query
    month_expr = func.date_trunc("month", BandwidthLedger.report_timestamp).cast(Date)

    agg_query = (
        db.query(
            BandwidthLedger.reporting_node_id.label("node_id"),
            month_expr.label("month"),
            func.sum(BandwidthLedger.bytes_transferred).label("total_bytes"),
            func.sum(
                case(
                    (BandwidthLedger.is_verified == True, BandwidthLedger.bytes_transferred),  # noqa: E712
                    else_=literal(0),
                )
            ).label("verified_bytes"),
            func.coalesce(func.avg(BandwidthLedger.trust_score), 0).label("avg_trust_score"),
            func.count().label("total_reports"),
        )
        .filter(BandwidthLedger.report_timestamp < cutoff)
        .group_by(BandwidthLedger.reporting_node_id, month_expr)
        .all()
    )

    if not agg_query:
        return 0

    for row in agg_query:
        # We need the user_id for the FK.  Look it up from the first
        # matching ledger entry (all entries for a node share the same
        # session which maps to a stream, but user_id lives on the node).
        # For simplicity, use a sub-query on the ledger's session → stream → node → user.
        # However, monthly_summaries.user_id is required.  The safest
        # approach: grab user_id from the Node table for this node_id.
        from .models import Node  # local import to avoid circular

        node = (
            db.query(Node.user_id)
            .filter(Node.node_id == row.node_id)
            .first()
        )
        user_id = node.user_id if node else "unknown"

        stmt = pg_insert(MonthlySummary).values(
            node_id=row.node_id,
            user_id=user_id,
            month=row.month,
            total_bytes=int(row.total_bytes),
            verified_bytes=int(row.verified_bytes),
            avg_trust_score=round(float(row.avg_trust_score), 2),
            total_reports=int(row.total_reports),
        )

        # ON CONFLICT (node_id, month) → accumulate
        stmt = stmt.on_conflict_do_update(
            constraint="uq_monthly_summary_node_month",
            set_={
                "total_bytes": MonthlySummary.total_bytes + stmt.excluded.total_bytes,
                "verified_bytes": MonthlySummary.verified_bytes + stmt.excluded.verified_bytes,
                "avg_trust_score": (
                    (MonthlySummary.avg_trust_score * MonthlySummary.total_reports
                     + stmt.excluded.avg_trust_score * stmt.excluded.total_reports)
                    / (MonthlySummary.total_reports + stmt.excluded.total_reports)
                ),
                "total_reports": MonthlySummary.total_reports + stmt.excluded.total_reports,
            },
        )
        db.execute(stmt)

    return len(agg_query)
