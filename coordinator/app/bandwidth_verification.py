"""
Bandwidth verification background task.
Task 5.1 — Req 13.1–13.3, Design §16

Runs every 15 minutes via APScheduler. Cross-references unverified bandwidth
reports with spot-check probe results and marks them verified/unverified.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_

from . import models
from .trust_scoring import recalculate_and_store, apply_trust_consequences

logger = logging.getLogger(__name__)

# Tolerance for claimed vs probe-estimated bytes (50%)
TOLERANCE = 0.50


def run_bandwidth_verification(db: Session) -> dict:
    """
    Verify unverified bandwidth reports by comparing against spot-check
    probe results for the same node in an overlapping time window.

    Returns a summary dict with counts.
    """
    now = datetime.now(timezone.utc)
    verified_count = 0
    failed_count = 0
    skipped_count = 0
    affected_nodes: set[str] = set()

    # Fetch all unverified reports
    unverified = (
        db.query(models.BandwidthLedger)
        .filter(models.BandwidthLedger.is_verified == False)  # noqa: E712
        .all()
    )

    if not unverified:
        logger.info("Bandwidth verification: no unverified reports")
        return {"verified": 0, "failed": 0, "skipped": 0}

    for report in unverified:
        # Find spot-check probes for this node overlapping the report interval
        # We look for probes within a generous window around the report period
        window_start = report.start_interval - timedelta(minutes=5)
        window_end = report.end_interval + timedelta(minutes=5)

        probes = (
            db.query(models.ProbeResult)
            .filter(
                and_(
                    models.ProbeResult.node_id == report.reporting_node_id,
                    models.ProbeResult.probe_type == "spot_check",
                    models.ProbeResult.probe_timestamp >= window_start,
                    models.ProbeResult.probe_timestamp <= window_end,
                )
            )
            .all()
        )

        if not probes:
            # No probe data to compare — skip, leave unverified for now
            skipped_count += 1
            continue

        # If any spot-check probe succeeded, the node was genuinely serving
        successful_probes = [p for p in probes if p.success]

        if successful_probes:
            # Node passed spot check during this window → mark verified
            report.is_verified = True
            report.verification_notes = (
                f"Verified: {len(successful_probes)}/{len(probes)} spot checks passed"
            )
            verified_count += 1
        else:
            # All probes failed — node was claiming bandwidth but not serving
            report.is_verified = False
            report.verification_notes = (
                f"Failed: 0/{len(probes)} spot checks passed during reporting window"
            )
            failed_count += 1

        affected_nodes.add(report.reporting_node_id)

    # Recalculate trust scores for all affected nodes
    for node_id in affected_nodes:
        score = recalculate_and_store(node_id, db)
        apply_trust_consequences(node_id, score, db)
        logger.info(
            "Trust score updated for node %s: %.2f", node_id, score
        )

    db.commit()

    summary = {
        "verified": verified_count,
        "failed": failed_count,
        "skipped": skipped_count,
    }
    logger.info(
        "Bandwidth verification complete: %d verified, %d failed, %d skipped",
        verified_count,
        failed_count,
        skipped_count,
    )
    return summary
