"""
Admin API routes for StreamrP2P Coordinator.
Tasks 4.10, 7.21

Provides:
- GET /api/v1/admin/mesh/nodes — VPN mesh status via Headscale API
- GET /api/v1/admin/validation-report — Aggregated validation metrics
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .headscale_client import get_headscale_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Task 4.10 — Mesh status endpoint
# ---------------------------------------------------------------------------

@router.get("/mesh/nodes")
async def mesh_nodes():
    """Return connected VPN mesh nodes from Headscale."""
    client = get_headscale_client()
    nodes = await client.list_nodes()
    return {"nodes": nodes, "count": len(nodes)}


# ---------------------------------------------------------------------------
# Task 7.21 — Validation report endpoint
# ---------------------------------------------------------------------------

@router.get("/validation-report")
async def validation_report(
    start: Optional[str] = Query(None, description="ISO 8601 start datetime"),
    end: Optional[str] = Query(None, description="ISO 8601 end datetime"),
    db: Session = Depends(get_db),
):
    """
    Aggregated validation metrics over a time range.

    Returns: stream uptime, node uptime, total bandwidth,
    payout accuracy, and viewer experience indicators.
    """
    now = datetime.now(timezone.utc)

    # Parse time range (default: last 24 hours)
    try:
        range_start = datetime.fromisoformat(start) if start else now - timedelta(hours=24)
    except ValueError:
        range_start = now - timedelta(hours=24)

    try:
        range_end = datetime.fromisoformat(end) if end else now
    except ValueError:
        range_end = now

    # --- Stream uptime ---
    total_streams = db.query(func.count(models.Stream.id)).scalar() or 0
    live_streams = (
        db.query(func.count(models.Stream.id))
        .filter(models.Stream.status == "LIVE")
        .scalar()
    ) or 0

    # --- Node uptime ---
    total_nodes = db.query(func.count(models.Node.id)).scalar() or 0
    active_nodes = (
        db.query(func.count(models.Node.id))
        .filter(models.Node.status == "active")
        .scalar()
    ) or 0

    # --- Total bandwidth in range ---
    total_bytes = (
        db.query(func.sum(models.BandwidthLedger.bytes_transferred))
        .filter(
            models.BandwidthLedger.report_timestamp >= range_start,
            models.BandwidthLedger.report_timestamp <= range_end,
        )
        .scalar()
    ) or 0

    verified_bytes = (
        db.query(func.sum(models.BandwidthLedger.bytes_transferred))
        .filter(
            models.BandwidthLedger.report_timestamp >= range_start,
            models.BandwidthLedger.report_timestamp <= range_end,
            models.BandwidthLedger.is_verified == True,  # noqa: E712
        )
        .scalar()
    ) or 0

    total_reports = (
        db.query(func.count(models.BandwidthLedger.id))
        .filter(
            models.BandwidthLedger.report_timestamp >= range_start,
            models.BandwidthLedger.report_timestamp <= range_end,
        )
        .scalar()
    ) or 0

    verified_reports = (
        db.query(func.count(models.BandwidthLedger.id))
        .filter(
            models.BandwidthLedger.report_timestamp >= range_start,
            models.BandwidthLedger.report_timestamp <= range_end,
            models.BandwidthLedger.is_verified == True,  # noqa: E712
        )
        .scalar()
    ) or 0

    # --- Payout accuracy ---
    payout_cycles = (
        db.query(func.count(models.PayoutLog.id))
        .filter(
            models.PayoutLog.cycle_timestamp >= range_start,
            models.PayoutLog.cycle_timestamp <= range_end,
        )
        .scalar()
    ) or 0

    total_paid_usd = (
        db.query(func.sum(models.PayoutLog.total_amount_usd))
        .filter(
            models.PayoutLog.cycle_timestamp >= range_start,
            models.PayoutLog.cycle_timestamp <= range_end,
        )
        .scalar()
    ) or Decimal("0")

    penalties_applied = (
        db.query(func.sum(models.PayoutLog.penalties_applied))
        .filter(
            models.PayoutLog.cycle_timestamp >= range_start,
            models.PayoutLog.cycle_timestamp <= range_end,
        )
        .scalar()
    ) or 0

    # --- Viewer experience ---
    avg_trust = (
        db.query(func.avg(models.UserAccount.trust_score)).scalar()
    ) or Decimal("0")

    flagged_nodes = (
        db.query(func.count(models.Node.id))
        .filter(models.Node.status == "flagged")
        .scalar()
    ) or 0

    total_gb = Decimal(str(total_bytes)) / Decimal(str(1024 ** 3))
    verified_gb = Decimal(str(verified_bytes)) / Decimal(str(1024 ** 3))
    verification_rate = (
        (verified_reports / total_reports * 100) if total_reports > 0 else 0
    )

    return {
        "range": {
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
        },
        "stream_uptime": {
            "total_streams": total_streams,
            "live_streams": live_streams,
            "live_pct": round(live_streams / total_streams * 100, 1) if total_streams else 0,
        },
        "node_uptime": {
            "total_nodes": total_nodes,
            "active_nodes": active_nodes,
            "active_pct": round(active_nodes / total_nodes * 100, 1) if total_nodes else 0,
            "flagged_nodes": flagged_nodes,
        },
        "bandwidth": {
            "total_bytes": total_bytes,
            "total_gb": float(total_gb.quantize(Decimal("0.01"))),
            "verified_gb": float(verified_gb.quantize(Decimal("0.01"))),
            "total_reports": total_reports,
            "verified_reports": verified_reports,
            "verification_rate_pct": round(verification_rate, 1),
        },
        "payout_accuracy": {
            "payout_cycles": payout_cycles,
            "total_paid_usd": float(total_paid_usd),
            "penalties_applied": penalties_applied,
        },
        "viewer_experience": {
            "avg_network_trust_score": float(
                Decimal(str(avg_trust)).quantize(Decimal("0.01"))
            ),
            "flagged_nodes": flagged_nodes,
        },
    }
