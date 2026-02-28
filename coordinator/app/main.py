#!/usr/bin/env python3
"""
StreamrP2P Coordinator API

Copyright (c) 2024-2025 Ian de Villiers. All Rights Reserved.
Proprietary and Confidential Software. Unauthorized use prohibited.
"""

from contextlib import asynccontextmanager
import logging
from uuid import uuid4

import structlog
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text as sa_text
from typing import List, Optional
import os
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

import secrets

from . import models, schemas, database
from .database import get_db, SessionLocal
from .payout_service import PayoutService
from .data_retention import run_data_retention
from .auth_routes import router as auth_router
from .stream_routes import router as stream_router
from .viewer_routes import router as viewer_router
from .proxy import router as proxy_router
from .auth import get_current_user, require_streamer, AuthenticatedUser
from .redis_state import get_redis, close_redis, update_node_state, cleanup_stale_nodes
from .bandwidth_verification import run_bandwidth_verification
from .economic_config import economic_config
from .trust_scoring import calculate_trust_score, apply_trust_consequences
from .feedback_routes import router as feedback_router
from .admin_routes import router as admin_router


load_dotenv()

# ---------------------------------------------------------------------------
# Structured logging with structlog (Task 7.1)
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# APScheduler — daily data-retention job at 03:00 UTC
# ---------------------------------------------------------------------------
scheduler = AsyncIOScheduler(timezone="UTC")


def _run_data_retention_job():
    """Wrapper executed by APScheduler in a sync context."""
    db = SessionLocal()
    try:
        run_data_retention(db)
    except Exception:
        logger.exception("Data retention job failed")
        db.rollback()
    finally:
        db.close()


scheduler.add_job(
    _run_data_retention_job,
    trigger=CronTrigger(hour=3, minute=0),
    id="data_retention",
    name="Daily data retention cleanup",
    replace_existing=True,
)


async def _cleanup_stale_nodes_job():
    """Remove nodes from Redis that haven't sent a heartbeat in 90s."""
    try:
        r = await get_redis()
        removed = await cleanup_stale_nodes(r, max_age_seconds=90)
        if removed:
            logger.info("Stale node cleanup: removed %d entries", removed)
    except Exception:
        logger.exception("Stale node cleanup failed")


from apscheduler.triggers.interval import IntervalTrigger

scheduler.add_job(
    _cleanup_stale_nodes_job,
    trigger=IntervalTrigger(seconds=30),
    id="stale_node_cleanup",
    name="Remove stale nodes from Redis (every 30s)",
    replace_existing=True,
)


def _run_bandwidth_verification_job():
    """Wrapper executed by APScheduler — verifies bandwidth reports every 15 min."""
    db = SessionLocal()
    try:
        run_bandwidth_verification(db)
    except Exception:
        logger.exception("Bandwidth verification job failed")
        db.rollback()
    finally:
        db.close()


scheduler.add_job(
    _run_bandwidth_verification_job,
    trigger=IntervalTrigger(minutes=15),
    id="bandwidth_verification",
    name="Verify bandwidth reports (every 15 min)",
    replace_existing=True,
)


def _run_payout_cycle_job():
    """Wrapper executed by APScheduler — hourly payout cycle."""
    db = SessionLocal()
    try:
        svc = PayoutService()
        svc.run_payout_cycle(db)
    except Exception:
        logger.exception("Hourly payout cycle failed")
        db.rollback()
    finally:
        db.close()


scheduler.add_job(
    _run_payout_cycle_job,
    trigger=CronTrigger(minute=0),  # top of every hour
    id="hourly_payout",
    name="Hourly payout cycle",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()
    logger.info("APScheduler started — data retention + stale node cleanup scheduled")
    yield
    # Shutdown
    scheduler.shutdown(wait=False)
    await close_redis()
    logger.info("APScheduler shut down")


app = FastAPI(
    title="StreamrP2P Coordinator",
    description="Proof of Concept coordinator for restreaming as support",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware (Req 3.1)
# ---------------------------------------------------------------------------
_cors_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate Limiting — slowapi (Req 3.2, 3.4)
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL")
_limiter_storage = f"redis://{REDIS_URL}" if REDIS_URL and not REDIS_URL.startswith("redis") else REDIS_URL

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=_limiter_storage,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ---------------------------------------------------------------------------
# Correlation ID middleware (Task 7.1)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
    )
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Mount auth routes
app.include_router(auth_router)

# Mount stream key management routes
app.include_router(stream_router)

# Mount viewer routing and HLS proxy
app.include_router(viewer_router)
app.include_router(proxy_router)
app.include_router(feedback_router)
app.include_router(admin_router)

# Initialize services
payout_service = PayoutService()


@app.get("/")
async def root():
    return {"message": "StreamrP2P Coordinator PoC", "version": "0.1.0"}

@app.post("/streams", response_model=schemas.StreamResponse)
async def register_stream(
    stream: schemas.StreamCreate,
    user: AuthenticatedUser = Depends(require_streamer),
    db: Session = Depends(get_db),
):
    """Register a new stream. Requires streamer role."""
    db_stream = models.Stream(
        stream_id=stream.stream_id,
        owner_user_id=user.user_id,
        stream_key=secrets.token_urlsafe(32),
        rtmp_url=stream.rtmp_url,
        status="READY",
    )
    db.add(db_stream)
    db.commit()
    db.refresh(db_stream)
    return db_stream

@app.get("/streams", response_model=List[schemas.StreamResponse])
async def list_streams(status: schemas.StreamStatusFilter = schemas.StreamStatusFilter.ALL, db: Session = Depends(get_db)):
    """List streams. For backward compatibility, returns all streams by default."""
    query = db.query(models.Stream)
    # Apply filter only if a status other than 'ALL' is provided
    if status != schemas.StreamStatusFilter.ALL:
        query = query.filter(models.Stream.status == status.value)
    
    streams = query.all()
    return streams

@app.get("/streams/live", response_model=List[schemas.StreamResponse])
async def get_live_streams(db: Session = Depends(get_db)):
    """Supporter discovery endpoint - only LIVE streams"""
    streams = db.query(models.Stream).filter(models.Stream.status == "LIVE").all()
    return streams

@app.patch("/streams/{stream_id}/status")
async def update_stream_status(
    stream_id: str, 
    status_update: schemas.StreamStatusUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manual status transitions for streamers. Only the stream owner can update."""
    stream = db.query(models.Stream).filter(models.Stream.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Ownership check
    if stream.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not the stream owner")
    
    # Validate state transitions
    valid_transitions = {
        'READY': ['TESTING', 'LIVE'],
        'TESTING': ['LIVE', 'OFFLINE', 'READY'], 
        'LIVE': ['OFFLINE'],
        'OFFLINE': ['READY', 'STALE', 'ARCHIVED'],  # Allow archiving from OFFLINE
        'STALE': ['READY', 'OFFLINE', 'ARCHIVED'],  # Allow recovery from STALE
        'ARCHIVED': []  # Terminal state, no transitions out
    }
    
    new_status = status_update.status.value
    if new_status not in valid_transitions.get(stream.status, []):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid transition: {stream.status} → {new_status}"
        )
    
    # Update status with timestamp
    stream.status = new_status
    if new_status == 'READY':
        # Clear all lifecycle timestamps for clean restart
        stream.testing_started_at = None
        stream.live_started_at = None
        stream.offline_at = None
        stream.stale_at = None
        stream.archived_at = None
    elif new_status == 'TESTING':
        stream.testing_started_at = datetime.now(timezone.utc)
    elif new_status == 'LIVE':
        stream.live_started_at = datetime.now(timezone.utc)
    elif new_status == 'OFFLINE':
        stream.offline_at = datetime.now(timezone.utc)
    elif new_status == 'STALE':
        stream.stale_at = datetime.now(timezone.utc)
    elif new_status == 'ARCHIVED':
        stream.archived_at = datetime.now(timezone.utc)
    
    db.commit()
    return {"status": "updated", "new_state": new_status}

@app.delete("/streams/{stream_id}")
async def delete_stream(
    stream_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a stream. Only the stream owner can delete."""
    stream = db.query(models.Stream).filter(models.Stream.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Ownership check
    if stream.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not the stream owner")
    
    # Also delete related nodes and probe results
    db.query(models.Node).filter(models.Node.stream_id == stream_id).delete()
    # Note: ProbeResult cleanup would go here if needed
    
    # Delete the stream
    db.delete(stream)
    db.commit()
    
    return {"status": "success", "message": f"Stream {stream_id} deleted"}

@app.post("/nodes/heartbeat")
async def node_heartbeat(
    heartbeat: schemas.NodeHeartbeat,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Receive heartbeat from node operators. JWT node_id must match payload."""
    # Verify JWT node_id matches heartbeat payload
    if user.node_id != heartbeat.node_id:
        raise HTTPException(status_code=403, detail="node_id mismatch with JWT")

    # Check if stream exists
    stream = db.query(models.Stream).filter(models.Stream.stream_id == heartbeat.stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Update or create node record
    node = db.query(models.Node).filter(
        models.Node.node_id == heartbeat.node_id,
        models.Node.stream_id == heartbeat.stream_id
    ).first()
    
    if node:
        node.stats_url = heartbeat.stats_url
        node.last_heartbeat = heartbeat.timestamp
        node.status = "active"
        if heartbeat.vpn_ip:
            node.vpn_ip = heartbeat.vpn_ip
        if heartbeat.capacity_pct is not None:
            node.capacity_pct = heartbeat.capacity_pct
    else:
        node = models.Node(
            node_id=heartbeat.node_id,
            stream_id=heartbeat.stream_id,
            stats_url=heartbeat.stats_url,
            last_heartbeat=heartbeat.timestamp,
            status="active",
            vpn_ip=heartbeat.vpn_ip or "",
            capacity_pct=heartbeat.capacity_pct or 0,
        )
        db.add(node)
    
    db.commit()

    # Update Redis state for fast peer lookups
    try:
        # Look up trust score from user account
        account = db.query(models.UserAccount).filter(
            models.UserAccount.user_id == user.user_id
        ).first()
        trust_score = float(account.trust_score) if account else 0.75

        r = await get_redis()
        await update_node_state(
            r,
            stream_id=heartbeat.stream_id,
            node_id=heartbeat.node_id,
            vpn_ip=node.vpn_ip or "",
            trust_score=trust_score,
            capacity_pct=node.capacity_pct or 0,
            viewer_count=0,  # updated by viewer routing
        )
    except Exception:
        logger.warning("Failed to update Redis node state for %s", heartbeat.node_id, exc_info=True)

    return {"status": "success", "message": "Heartbeat received"}

@app.get("/dashboard")
async def dashboard(limit: int = 10, node_statuses: str = "active", db: Session = Depends(get_db)):
    """
    Dashboard showing streams and nodes with flexible filtering
    
    Args:
        limit (int): Maximum number of streams to return (default: 10)
        node_statuses (str): Comma-separated node statuses to filter by (e.g., "active,inactive")
        db: Database session
    """
    # Updated for Stream Lifecycle System - show operational streams
    operational_statuses = ["READY", "TESTING", "LIVE", "OFFLINE"]
    
    # Parse and validate node statuses (filter out empty strings)
    valid_node_statuses = {"active", "inactive", "flagged"}  # Define valid statuses
    raw_statuses = [s.strip() for s in node_statuses.split(",") if s.strip()]
    node_status_list = [status for status in raw_statuses if status in valid_node_statuses]
    
    # Check for invalid statuses and provide clear error message
    invalid_statuses = set(raw_statuses) - set(node_status_list)
    if invalid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid node status(es) provided: {', '.join(invalid_statuses)}. Valid statuses are: {', '.join(valid_node_statuses)}"
        )
    
    # Default to "active" only if no statuses were provided at all
    if not node_status_list:
        node_status_list = ["active"]
    
    # PERFORMANCE FIX: Use only 2 database queries instead of N+1
    
    # Query 1: Get streams
    streams = db.query(models.Stream).filter(
        models.Stream.status.in_(operational_statuses)
    ).limit(limit).all()
    
    if not streams:
        return {"streams": []}
    
    # Query 2: Get all relevant nodes in a single query
    stream_ids = [s.stream_id for s in streams]
    all_nodes = db.query(models.Node).filter(
        models.Node.stream_id.in_(stream_ids),
        models.Node.status.in_(node_status_list)
    ).all()
    
    # Map nodes to their stream_id for efficient lookup
    nodes_by_stream_id = {}
    for node in all_nodes:
        nodes_by_stream_id.setdefault(node.stream_id, []).append(node)
    
    # Build response without additional queries
    dashboard_data = []
    for stream in streams:
        stream_nodes = nodes_by_stream_id.get(stream.stream_id, [])
        
        dashboard_data.append({
            "stream_id": stream.stream_id,
            "owner_user_id": stream.owner_user_id,
            "status": stream.status,
            "node_count": len(stream_nodes),
            "nodes": [{"node_id": n.node_id, "stats_url": n.stats_url} for n in stream_nodes]
        })
    
    return {"streams": dashboard_data}

@app.get("/payouts")
async def get_payouts(hours_back: int = 1, db: Session = Depends(get_db)):
    """Calculate and return payout information for the specified time period"""
    try:
        payouts = payout_service.calculate_payouts(db, hours_back)
        return {
            "status": "success",
            "calculation_time": f"Last {hours_back} hour(s)",
            "payouts": payouts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating payouts: {str(e)}")

@app.get("/nodes/{node_id}/earnings")
async def get_node_earnings(node_id: str, days_back: int = 7, db: Session = Depends(get_db)):
    """Get earnings summary for a specific node"""
    try:
        earnings = payout_service.get_node_earnings_summary(db, node_id, days_back)
        return earnings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting node earnings: {str(e)}")

@app.get("/leaderboard")
async def get_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    """Get top performing nodes leaderboard"""
    try:
        leaderboard = payout_service.get_leaderboard(db, limit)
        return {
            "status": "success",
            "leaderboard": leaderboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting leaderboard: {str(e)}")

# ===== ECONOMIC VALIDATION ENDPOINTS =====

@app.get("/economic-dashboard", response_class=HTMLResponse)
async def economic_dashboard():
    """Serve the economic validation HTML dashboard"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "economic_dashboard.html")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dashboard template not found")

@app.get("/streams-dashboard", response_class=HTMLResponse)
async def streams_dashboard():
    """Serve the streams management HTML dashboard"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "streams_dashboard.html")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Streams dashboard template not found")


# ---------------------------------------------------------------------------
# Frontend Dashboards (Batch C — Tasks 6.1, 6.2, 6.3)
# ---------------------------------------------------------------------------

def _serve_template(name: str) -> HTMLResponse:
    path = os.path.join(os.path.dirname(__file__), "templates", name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template {name} not found")


@app.get("/dashboard/streamer/{stream_id}", response_class=HTMLResponse)
async def streamer_dashboard(stream_id: str):
    """Streamer dashboard — stream status, active nodes, bandwidth, cost savings."""
    return _serve_template("streamer_dashboard.html")


@app.get("/dashboard/node/{node_id}", response_class=HTMLResponse)
async def node_dashboard(node_id: str):
    """Friend node dashboard — earnings, trust score, chart, feedback form."""
    return _serve_template("node_dashboard.html")


@app.get("/watch/{stream_id}", response_class=HTMLResponse)
async def watch_page(stream_id: str):
    """Viewer page — HLS.js player with auto-reconnect and source type status."""
    return _serve_template("viewer.html")

@app.post("/api/v1/sessions/{session_id}/bandwidth-report", response_model=schemas.BandwidthReportResponse)
async def report_bandwidth(
    session_id: str,
    report: schemas.BandwidthReport,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept bandwidth usage reports from node clients.
    Performs basic validation and queues for verification.
    """
    # Verify session exists
    stream = db.query(models.Stream).filter(models.Stream.stream_id == session_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify reporting node exists and is associated with this stream
    node = db.query(models.Node).filter(
        models.Node.node_id == user.node_id,
        models.Node.stream_id == session_id
    ).first()
    if not node:
        raise HTTPException(status_code=403, detail="Node not authorized for this session")
    
    # Basic validation
    if report.bytes_transferred < 0:
        raise HTTPException(status_code=400, detail="Invalid bytes_transferred value")
    
    if report.end_interval <= report.start_interval:
        raise HTTPException(status_code=400, detail="Invalid time interval")
    
    # Create bandwidth ledger entry
    bandwidth_entry = models.BandwidthLedger(
        session_id=session_id,
        reporting_node_id=user.node_id,
        bytes_transferred=report.bytes_transferred,
        start_interval=report.start_interval,
        end_interval=report.end_interval,
        source_bitrate_kbps=report.source_bitrate_kbps,
        is_verified=False,  # Will be verified by background task
        trust_score=None,   # Will be calculated by verification
        verification_notes=None
    )
    
    db.add(bandwidth_entry)
    db.commit()
    db.refresh(bandwidth_entry)
    
    # TODO: Trigger async verification task
    
    return bandwidth_entry

@app.get("/api/v1/economics/dashboard", response_model=schemas.EconomicsDashboard)
async def get_economics_dashboard(db: Session = Depends(get_db)):
    """
    Return summary data for the economic validation dashboard.
    """
    # Get current timestamp for 24h calculations
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    # Basic metrics
    active_sessions = db.query(models.Stream).filter(
        models.Stream.status.in_(["READY", "TESTING", "LIVE"])
    ).count()
    
    total_nodes = db.query(models.Node).filter(
        models.Node.status == "active"
    ).count()
    
    # Total GB delivered in last 24h
    gb_24h_result = db.query(func.sum(models.BandwidthLedger.bytes_transferred)).filter(
        models.BandwidthLedger.report_timestamp >= twenty_four_hours_ago,
        models.BandwidthLedger.is_verified == True
    ).scalar()
    total_gb_delivered_24h = Decimal(str((gb_24h_result or 0) / (1024**3)))  # Convert bytes to GB
    
    # Platform economics (placeholder calculations)
    platform_margin_percent = Decimal("7.5")  # Example: 7.5% margin
    avg_creator_revenue_share = Decimal("87.5")  # Example: 87.5% to creators
    
    # Qualified earners (nodes earning $50-200/month)
    qualified_earners = db.query(models.UserAccount).filter(
        models.UserAccount.earnings_last_30d >= Decimal("50.00"),
        models.UserAccount.earnings_last_30d <= Decimal("200.00")
    ).count()
    
    # Top earners
    top_earners_query = db.query(models.UserAccount).filter(
        models.UserAccount.earnings_last_30d > 0
    ).order_by(desc(models.UserAccount.earnings_last_30d)).limit(5).all()
    
    top_earners = []
    for account in top_earners_query:
        top_earners.append({
            "node_id": account.user_id[:8] + "...",  # Truncate for privacy
            "earnings": float(account.earnings_last_30d),
            "gb_relayed": float(account.total_gb_relayed),
            "trust_score": float(account.trust_score)
        })
    
    # Suspicious activity (low trust scores)
    suspicious_reports = db.query(models.BandwidthLedger).filter(
        models.BandwidthLedger.trust_score < Decimal("0.8"),
        models.BandwidthLedger.report_timestamp >= twenty_four_hours_ago
    ).count()
    
    suspicious_activity = [
        {
            "type": "low_trust_reports",
            "count": suspicious_reports,
            "description": "Bandwidth reports with trust score < 0.8"
        }
    ]
    
    return schemas.EconomicsDashboard(
        active_sessions=active_sessions,
        total_nodes=total_nodes,
        total_gb_delivered_24h=total_gb_delivered_24h,
        platform_margin_percent=platform_margin_percent,
        avg_creator_revenue_share=avg_creator_revenue_share,
        qualified_earners_count=qualified_earners,
        top_earners=top_earners,
        suspicious_activity=suspicious_activity
    )

async def get_node_economics(node_id: str, db: Session = Depends(get_db)):
    """
    Detailed economic data for a specific node.
    Includes live trust score calculation.
    """
    # Resolve node_id → user_id via the Node table
    node = db.query(models.Node).filter(models.Node.node_id == node_id).first()
    user_id = node.user_id if node else node_id

    # Get or create user account
    user_account = db.query(models.UserAccount).filter(
        models.UserAccount.user_id == user_id
    ).first()

    if not user_account:
        # Create default account if doesn't exist
        user_account = models.UserAccount(
            user_id=user_id,
            balance_usd=Decimal("0.00"),
            total_gb_relayed=Decimal("0.00"),
            earnings_last_30d=Decimal("0.00"),
            trust_score=Decimal("0.75"),
            flags=[],
            last_updated_at=datetime.now(timezone.utc)
        )
        db.add(user_account)
        db.commit()
        db.refresh(user_account)

    # Recalculate trust score from bandwidth ledger data
    live_trust = calculate_trust_score(node_id, db)
    if user_account.trust_score != live_trust:
        user_account.trust_score = live_trust
        user_account.last_updated_at = datetime.now(timezone.utc)
        apply_trust_consequences(node_id, live_trust, db)
        db.commit()

    # Calculate hourly earnings for last 24 hours from payout_log_entries
    hourly_earnings = []
    for i in range(24):
        hour_start = datetime.now(timezone.utc) - timedelta(hours=i+1)
        hour_end = datetime.now(timezone.utc) - timedelta(hours=i)

        hour_entry = db.query(
            func.sum(models.PayoutLogEntry.earnings_usd).label("earnings"),
            func.sum(models.PayoutLogEntry.bytes_relayed).label("bytes"),
        ).filter(
            models.PayoutLogEntry.node_id == node_id,
            models.PayoutLogEntry.timestamp >= hour_start,
            models.PayoutLogEntry.timestamp < hour_end,
        ).first()

        hourly_earnings.append({
            "hour": hour_start.strftime("%H:00"),
            "earnings_usd": float(hour_entry.earnings or 0),
            "gb_relayed": float((hour_entry.bytes or 0) / (1024**3)),
        })

    return schemas.NodeEconomics(
        node_id=node_id,
        balance_usd=user_account.balance_usd,
        earnings_last_30d=user_account.earnings_last_30d,
        gb_relayed=user_account.total_gb_relayed,
        trust_score=user_account.trust_score,
        hourly_earnings=hourly_earnings
    )

@app.get("/api/v1/streams/{stream_id}/peers")
async def get_stream_peers(stream_id: str):
    """
    Return active nodes for a stream, ordered by trust_score DESC,
    filtered to capacity_pct < 90.  Data sourced from Redis for speed.
    """
    try:
        r = await get_redis()
        from .redis_state import get_stream_nodes
        nodes = await get_stream_nodes(r, stream_id)
    except Exception:
        logger.warning("Redis unavailable for peer list, returning empty", exc_info=True)
        return []

    # Filter out saturated nodes and sort by trust_score descending
    active = [
        {
            "node_id": n["node_id"],
            "vpn_ip": n.get("vpn_ip", ""),
            "trust_score": n.get("trust_score", 0),
            "capacity_pct": n.get("capacity_pct", 0),
            "viewer_count": n.get("viewer_count", 0),
        }
        for n in nodes
        if n.get("capacity_pct", 0) < 90
    ]
    active.sort(key=lambda n: n["trust_score"], reverse=True)
    return active


@app.get("/api/v1/economics/node/{node_id}/earnings", response_model=schemas.EarningsResponse)
async def get_node_earnings_history(
    node_id: str,
    days: int = 7,
    db: Session = Depends(get_db),
):
    """
    Earnings history for a node over the given period.
    Returns hourly payout_log_entries with timestamp, bytes, earnings, trust.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
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
    return schemas.EarningsResponse(
        node_id=node_id,
        period={"start": cutoff.isoformat(), "end": datetime.now(timezone.utc).isoformat()},
        total_earnings_usd=str(total),
        entries=[
            schemas.PayoutLogEntryResponse(
                timestamp=e.timestamp,
                bytes_relayed=e.bytes_relayed,
                earnings_usd=str(e.earnings_usd),
                trust_score=str(e.trust_score),
                penalty_applied=e.penalty_applied,
            )
            for e in entries
        ],
    )


@app.get("/api/v1/economics/config")
async def get_economics_config():
    """Read-only endpoint exposing current economic parameters. No auth required (transparency)."""
    return economic_config.to_dict()


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Enhanced health check — verifies database, Redis, and background workers.
    Returns healthy | degraded | unhealthy with per-check details.
    """
    checks = {}
    overall = "healthy"

    # Database check
    try:
        db.execute(sa_text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}
        overall = "unhealthy"

    # Redis check
    try:
        r = await get_redis()
        await r.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}
        if overall == "healthy":
            overall = "degraded"

    # Background scheduler check
    if scheduler.running:
        jobs = {j.id: str(j.next_run_time) for j in scheduler.get_jobs()}
        checks["scheduler"] = {"status": "ok", "jobs": jobs}
    else:
        checks["scheduler"] = {"status": "error", "detail": "scheduler not running"}
        if overall == "healthy":
            overall = "degraded"

    status_code = 200 if overall != "unhealthy" else 503
    from starlette.responses import JSONResponse
    return JSONResponse(
        content={"status": overall, "service": "coordinator", "checks": checks},
        status_code=status_code,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 