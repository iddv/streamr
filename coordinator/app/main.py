#!/usr/bin/env python3
"""
StreamrP2P Coordinator API

Copyright (c) 2024-2025 Ian de Villiers. All Rights Reserved.
Proprietary and Confidential Software. Unauthorized use prohibited.
"""

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import os
from dotenv import load_dotenv

from . import models, schemas, database
from .database import get_db
from .payout_service import PayoutService
from datetime import datetime

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
        status="active"
    )
    db.add(db_stream)
    db.commit()
    db.refresh(db_stream)
    return db_stream

@app.get("/streams", response_model=List[schemas.StreamResponse])
async def list_streams(db: Session = Depends(get_db)):
    """List all streams (for admin/debugging)"""
    streams = db.query(models.Stream).all()
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
        'OFFLINE': ['READY']  # Allow restart
    }
    
    new_status = status_update.status.value
    if new_status not in valid_transitions.get(stream.status, []):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid transition: {stream.status} → {new_status}"
        )
    
    # Update status with timestamp
    stream.status = new_status
    if new_status == 'TESTING':
        stream.testing_started_at = datetime.utcnow()
    elif new_status == 'LIVE':
        stream.live_started_at = datetime.utcnow()
    elif new_status == 'OFFLINE':
        stream.offline_at = datetime.utcnow()
    
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
async def dashboard(db: Session = Depends(get_db)):
    """Simple dashboard showing active streams and nodes"""
    streams = db.query(models.Stream).filter(models.Stream.status == "active").all()
    dashboard_data = []
    
    for stream in streams:
        nodes = db.query(models.Node).filter(
            models.Node.stream_id == stream.stream_id,
            models.Node.status == "active"
        ).all()
        
        dashboard_data.append({
            "stream_id": stream.stream_id,
            "sponsor": stream.sponsor_address,
            "token_balance": stream.token_balance,
            "active_nodes": len(nodes),
            "nodes": [{"node_id": n.node_id, "stats_url": n.stats_url} for n in nodes]
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "coordinator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 