#!/usr/bin/env python3
"""
StreamrP2P Coordinator API

Copyright (c) 2024-2025 Ian de Villiers. All Rights Reserved.
Proprietary and Confidential Software. Unauthorized use prohibited.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
import os
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime, timedelta

from . import models, schemas, database
from .database import get_db
from .payout_service import PayoutService
from .migration_endpoints import router as migration_router

load_dotenv()

app = FastAPI(
    title="StreamrP2P Coordinator",
    description="Proof of Concept coordinator for restreaming as support",
    version="0.1.0"
)

# Initialize database
models.Base.metadata.create_all(bind=database.engine)

# Initialize services
payout_service = PayoutService()

# Include routers
app.include_router(migration_router)

# Helper function for authentication (placeholder)
async def get_authenticated_node(db: Session = Depends(get_db)) -> str:
    """Placeholder for node authentication - returns a dummy node_id for now"""
    # TODO: Implement proper JWT or API key authentication
    return "dummy_node_id"

@app.get("/")
async def root():
    return {"message": "StreamrP2P Coordinator PoC", "version": "0.1.0"}

@app.post("/streams", response_model=schemas.StreamResponse)
async def register_stream(stream: schemas.StreamCreate, db: Session = Depends(get_db)):
    """Register a new stream with fake token sponsorship"""
    db_stream = models.Stream(
        stream_id=stream.stream_id,
        sponsor_address=stream.sponsor_address,
        token_balance=stream.token_balance,
        rtmp_url=stream.rtmp_url,
        status="READY"  # Updated for Stream Lifecycle System
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
    db: Session = Depends(get_db)
):
    """Manual status transitions for streamers"""
    stream = db.query(models.Stream).filter(models.Stream.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
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
        stream.testing_started_at = datetime.utcnow()
    elif new_status == 'LIVE':
        stream.live_started_at = datetime.utcnow()
    elif new_status == 'OFFLINE':
        stream.offline_at = datetime.utcnow()
    elif new_status == 'STALE':
        stream.stale_at = datetime.utcnow()
    elif new_status == 'ARCHIVED':
        stream.archived_at = datetime.utcnow()
    
    db.commit()
    return {"status": "updated", "new_state": new_status}

@app.delete("/streams/{stream_id}")
async def delete_stream(stream_id: str, db: Session = Depends(get_db)):
    """Delete a stream (cleanup old/inactive streams)"""
    stream = db.query(models.Stream).filter(models.Stream.stream_id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Also delete related nodes and probe results
    db.query(models.Node).filter(models.Node.stream_id == stream_id).delete()
    # Note: ProbeResult cleanup would go here if needed
    
    # Delete the stream
    db.delete(stream)
    db.commit()
    
    return {"status": "success", "message": f"Stream {stream_id} deleted"}

@app.post("/nodes/heartbeat")
async def node_heartbeat(heartbeat: schemas.NodeHeartbeat, db: Session = Depends(get_db)):
    """Receive heartbeat from node operators"""
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
    else:
        node = models.Node(
            node_id=heartbeat.node_id,
            stream_id=heartbeat.stream_id,
            stats_url=heartbeat.stats_url,
            last_heartbeat=heartbeat.timestamp,
            status="active"
        )
        db.add(node)
    
    db.commit()
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
            "sponsor": stream.sponsor_address,
            "token_balance": stream.token_balance,
            "status": stream.status,
            "node_count": len(stream_nodes),
            "nodes": [{"node_id": n.node_id, "stats_url": n.stats_url} for n in stream_nodes]
        })
    
    return {"streams": dashboard_data}

@app.get("/payouts")
async def get_payouts(hours_back: int = 1):
    """Calculate and return payout information for the specified time period"""
    try:
        payouts = payout_service.calculate_payouts(hours_back)
        return {
            "status": "success",
            "calculation_time": f"Last {hours_back} hour(s)",
            "payouts": payouts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating payouts: {str(e)}")

@app.get("/nodes/{node_id}/earnings")
async def get_node_earnings(node_id: str, days_back: int = 7):
    """Get earnings summary for a specific node"""
    try:
        earnings = payout_service.get_node_earnings_summary(node_id, days_back)
        return earnings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting node earnings: {str(e)}")

@app.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get top performing nodes leaderboard"""
    try:
        leaderboard = payout_service.get_leaderboard(limit)
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

@app.post("/api/v1/sessions/{session_id}/bandwidth-report", response_model=schemas.BandwidthReportResponse)
async def report_bandwidth(
    session_id: str,
    report: schemas.BandwidthReport,
    current_node: str = Depends(get_authenticated_node),
    db: Session = Depends(get_db)
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
        models.Node.node_id == current_node,
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
        reporting_node_id=current_node,
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
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
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

@app.get("/api/v1/economics/node/{node_id}", response_model=schemas.NodeEconomics)
async def get_node_economics(node_id: str, db: Session = Depends(get_db)):
    """
    Detailed economic data for a specific node.
    """
    # Get or create user account
    user_account = db.query(models.UserAccount).filter(
        models.UserAccount.user_id == node_id
    ).first()
    
    if not user_account:
        # Create default account if doesn't exist
        user_account = models.UserAccount(
            user_id=node_id,
            balance_usd=Decimal("0.00"),
            total_gb_relayed=Decimal("0.00"),
            earnings_last_30d=Decimal("0.00"),
            trust_score=Decimal("1.00"),
            flags=[],
            last_updated_at=datetime.utcnow()
        )
        db.add(user_account)
        db.commit()
        db.refresh(user_account)
    
    # Calculate hourly earnings for last 24 hours (placeholder)
    hourly_earnings = []
    for i in range(24):
        hour_start = datetime.utcnow() - timedelta(hours=i+1)
        hour_end = datetime.utcnow() - timedelta(hours=i)
        
        # Placeholder calculation - in real implementation, this would be based on actual bandwidth reports
        hourly_earnings.append({
            "hour": hour_start.strftime("%H:00"),
            "earnings_usd": float(Decimal("0.25")),  # Example: $0.25/hour
            "gb_relayed": float(Decimal("1.2"))      # Example: 1.2 GB/hour
        })
    
    return schemas.NodeEconomics(
        node_id=node_id,
        balance_usd=user_account.balance_usd,
        earnings_last_30d=user_account.earnings_last_30d,
        gb_relayed=user_account.total_gb_relayed,
        trust_score=user_account.trust_score,
        hourly_earnings=hourly_earnings
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "coordinator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 