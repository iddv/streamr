# 🔄 Stream Lifecycle Management - Development Plan

> **Based on**: ZEN Advisor consultations + Industry best practices (Twitch, YouTube Live)  
> **Replaces**: Simple DELETE endpoints with enterprise-grade status management  
> **Timeline**: 4-week implementation for friends testing phase

## 📋 Executive Summary

Transform StreamrP2P from basic stream registration to sophisticated lifecycle management with:
- **Status-based lifecycle**: READY → TESTING → LIVE → OFFLINE → STALE → ARCHIVED
- **Broadcast vs IngestProfile separation**: Event metadata vs reusable technical configs
- **Advanced analytics pipeline**: Real-time performance tracking + historical optimization
- **Smart supporter allocation**: AI-driven node assignment based on stream reliability

## 🎯 Phase 1: Core State Machine (Week 1)

### **Database Schema Changes**

```sql
-- 1. Add lifecycle fields to existing streams table
ALTER TABLE streams ADD COLUMN status VARCHAR(20) DEFAULT 'READY';
ALTER TABLE streams ADD COLUMN live_started_at TIMESTAMP;
ALTER TABLE streams ADD COLUMN offline_at TIMESTAMP;
ALTER TABLE streams ADD COLUMN testing_started_at TIMESTAMP;

-- 2. Create index for status-based queries
CREATE INDEX idx_streams_status_discovery ON streams(status, live_started_at);

-- 3. Clean up stale data
UPDATE streams SET status = 'OFFLINE', offline_at = NOW() 
WHERE stream_id = 'obs-test' AND created_at < NOW() - INTERVAL '1 day';
```

### **API Endpoints**

```python
# coordinator/app/main.py additions

@app.patch("/streams/{stream_id}/status")
async def update_stream_status(
    stream_id: str, 
    status: StreamStatus,
    db: Session = Depends(get_db)
):
    """Manual status transitions for streamers"""
    stream = get_stream_or_404(db, stream_id)
    
    # Validate state transitions
    valid_transitions = {
        'READY': ['TESTING', 'LIVE'],
        'TESTING': ['LIVE', 'OFFLINE', 'READY'], 
        'LIVE': ['OFFLINE'],
        'OFFLINE': ['READY']  # Allow restart
    }
    
    if status.value not in valid_transitions.get(stream.status, []):
        raise HTTPException(400, f"Invalid transition: {stream.status} → {status.value}")
    
    # Update status with timestamp
    stream.status = status.value
    if status.value == 'TESTING':
        stream.testing_started_at = datetime.utcnow()
    elif status.value == 'LIVE':
        stream.live_started_at = datetime.utcnow()
    elif status.value == 'OFFLINE':
        stream.offline_at = datetime.utcnow()
    
    db.commit()
    return {"status": "updated", "new_state": status.value}

@app.get("/streams/live")
async def get_live_streams(db: Session = Depends(get_db)):
    """Supporter discovery endpoint - only LIVE streams"""
    return db.query(models.Stream).filter(
        models.Stream.status == 'LIVE'
    ).all()
```

### **Heartbeat System**

```python
# coordinator/app/heartbeat.py (new file)
import redis
from celery import Celery
from datetime import datetime, timedelta

redis_client = redis.Redis(host=settings.REDIS_HOST)
celery_app = Celery('heartbeat')

@celery_app.task
def reaper_worker():
    """Check for dead streams every 30 seconds"""
    # Get all LIVE/TESTING streams
    live_streams = db.query(models.Stream).filter(
        models.Stream.status.in_(['LIVE', 'TESTING'])
    ).all()
    
    # Check heartbeats
    stream_ids = [s.stream_id for s in live_streams]
    health_keys = [f"stream:health:{sid}" for sid in stream_ids]
    health_status = redis_client.mget(health_keys)
    
    # Mark dead streams as OFFLINE
    dead_streams = [
        stream_ids[i] for i, status in enumerate(health_status) 
        if status is None
    ]
    
    if dead_streams:
        db.query(models.Stream).filter(
            models.Stream.stream_id.in_(dead_streams)
        ).update({
            'status': 'OFFLINE',
            'offline_at': datetime.utcnow()
        })
        db.commit()
        logger.info(f"Marked {len(dead_streams)} streams as OFFLINE")

# Schedule reaper worker every 30 seconds
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(30.0, reaper_worker.s(), name='stream-reaper')
```

### **Testing & Validation**

```bash
# 1. Start coordinator with new lifecycle endpoints
cd coordinator && uvicorn app.main:app --reload

# 2. Test manual state transitions
curl -X PATCH "http://localhost:8000/streams/iddv-stream/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "LIVE"}'

# 3. Test heartbeat system
redis-cli SETEX stream:health:iddv-stream 60 "LIVE"
redis-cli GET stream:health:iddv-stream  # Should return "LIVE"
sleep 61
redis-cli GET stream:health:iddv-stream  # Should return nil

# 4. Test supporter discovery
curl "http://localhost:8000/streams/live"  # Should only return LIVE streams
```

---

## 🏗️ Phase 2: Broadcast vs IngestProfile Architecture (Week 2)

### **Enhanced Database Schema**

```sql
-- Separate stream configuration from broadcast events
CREATE TABLE ingest_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,  -- When user system exists
    name VARCHAR(100) NOT NULL,  -- "Home OBS Setup"
    stream_key VARCHAR(64) UNIQUE NOT NULL,
    ingest_server_url VARCHAR(255) NOT NULL,
    target_bitrate_kbps INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,
    
    -- Performance analytics (calculated by background jobs)
    total_broadcasts INTEGER DEFAULT 0,
    avg_actual_bitrate_kbps INTEGER,
    avg_duration_minutes INTEGER,
    stability_score FLOAT DEFAULT 0.0,
    avg_supporter_nodes_required INTEGER DEFAULT 5
);

CREATE TABLE broadcasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingest_profile_id UUID REFERENCES ingest_profiles(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'READY',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    testing_started_at TIMESTAMP,
    live_started_at TIMESTAMP,
    offline_at TIMESTAMP,
    
    -- Migrate from existing streams table
    stream_id VARCHAR(100) UNIQUE NOT NULL,  -- Keep for RTMP compatibility
    sponsor_address VARCHAR(100),
    token_balance FLOAT,
    rtmp_url VARCHAR(255)
);

-- Migration script
INSERT INTO ingest_profiles (name, stream_key, ingest_server_url, target_bitrate_kbps)
SELECT 
    CONCAT('Profile for ', stream_id),
    stream_id,
    rtmp_url,
    3000  -- Default bitrate
FROM streams WHERE status != 'ARCHIVED';

INSERT INTO broadcasts (ingest_profile_id, title, stream_id, status, live_started_at)
SELECT 
    p.id,
    CONCAT('Broadcast for ', s.stream_id),
    s.stream_id,
    s.status,
    s.live_started_at
FROM streams s
JOIN ingest_profiles p ON s.stream_id = p.stream_key;
```

### **New API Endpoints**

```python
# Enhanced coordinator API
@app.post("/ingest-profiles", response_model=schemas.IngestProfileResponse)
async def create_ingest_profile(
    profile: schemas.IngestProfileCreate,
    db: Session = Depends(get_db)
):
    """Create reusable streaming configuration"""
    # Generate unique stream key
    stream_key = generate_stream_key()
    
    db_profile = models.IngestProfile(
        name=profile.name,
        stream_key=stream_key,
        ingest_server_url=f"rtmp://{settings.INGEST_SERVER_IP}:1935/live/{stream_key}",
        target_bitrate_kbps=profile.target_bitrate_kbps or 3000
    )
    db.add(db_profile)
    db.commit()
    return db_profile

@app.post("/broadcasts", response_model=schemas.BroadcastResponse)
async def create_broadcast(
    broadcast: schemas.BroadcastCreate,
    db: Session = Depends(get_db)
):
    """Create new streaming event"""
    profile = get_ingest_profile_or_404(db, broadcast.ingest_profile_id)
    
    db_broadcast = models.Broadcast(
        ingest_profile_id=broadcast.ingest_profile_id,
        title=broadcast.title,
        description=broadcast.description,
        stream_id=profile.stream_key  # Use profile's stream key
    )
    db.add(db_broadcast)
    db.commit()
    return db_broadcast

@app.get("/ingest-profiles/{profile_id}/analytics")
async def get_profile_analytics(
    profile_id: UUID,
    db: Session = Depends(get_db)
):
    """Performance dashboard for streamers"""
    profile = get_ingest_profile_or_404(db, profile_id)
    
    return {
        "name": profile.name,
        "total_broadcasts": profile.total_broadcasts,
        "avg_duration_minutes": profile.avg_duration_minutes,
        "stability_score": profile.stability_score,
        "target_vs_actual_bitrate": {
            "target": profile.target_bitrate_kbps,
            "actual": profile.avg_actual_bitrate_kbps,
            "efficiency": profile.avg_actual_bitrate_kbps / profile.target_bitrate_kbps if profile.target_bitrate_kbps else 0
        },
        "supporter_requirements": {
            "avg_nodes": profile.avg_supporter_nodes_required,
            "recommendation": "optimal" if profile.stability_score > 0.9 else "needs_improvement"
        }
    }
```

---

## 📊 Phase 3: Analytics Pipeline (Week 3)

### **Session Summary Events**

```python
# ingest_server/session_tracker.py (integrate with SRS)
from pydantic import BaseModel
import json
import boto3

class StreamSessionSummary(BaseModel):
    broadcast_id: str
    session_start_ts: int
    session_end_ts: int
    total_bytes_received: int
    target_bitrate_kbps: int
    actual_avg_bitrate_kbps: int
    micro_disconnects: int
    micro_disconnect_total_seconds: int
    end_reason: str  # "streamer_stopped", "connection_lost", "timeout"

def emit_session_summary(session_data: StreamSessionSummary):
    """Emit session summary to SQS for processing"""
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl=settings.ANALYTICS_QUEUE_URL,
        MessageBody=session_data.json()
    )
```

### **Analytics Processing Worker**

```python
# coordinator/app/analytics.py
@celery_app.task(bind=True, max_retries=3)
def process_session_analytics(self, session_event):
    """Orchestrate analytics from multiple data sources"""
    try:
        # Parse ingest server data
        stream_data = StreamSessionSummary.parse_raw(session_event)
        
        # Fetch P2P metrics from coordinator  
        p2p_response = requests.get(
            f"{COORDINATOR_API}/broadcasts/{stream_data.broadcast_id}/p2p-summary",
            timeout=30
        )
        p2p_data = P2PSessionSummary.parse_obj(p2p_response.json())
        
        # Calculate combined analytics
        analytics = calculate_session_metrics(stream_data, p2p_data)
        
        # Store detailed analytics
        db_analytics = models.BroadcastAnalytics(
            broadcast_id=stream_data.broadcast_id,
            session_duration_seconds=stream_data.session_end_ts - stream_data.session_start_ts,
            stability_score=analytics.stability_score,
            bitrate_efficiency=analytics.bitrate_efficiency,
            supporter_efficiency=analytics.supporter_efficiency,
            raw_stream_data=stream_data.json(),
            raw_p2p_data=p2p_data.json()
        )
        db.add(db_analytics)
        
        # Update IngestProfile aggregates
        update_profile_aggregates(stream_data.broadcast_id, analytics)
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Analytics processing failed: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))

def calculate_session_metrics(stream_data, p2p_data):
    """Business logic for calculating performance scores"""
    config = AnalyticsConfig.load()
    
    # Stability score accounting for micro-disconnects
    session_duration = stream_data.session_end_ts - stream_data.session_start_ts
    micro_penalty = stream_data.micro_disconnects * config.micro_disconnect_penalty_seconds
    disruption_penalty = stream_data.micro_disconnect_total_seconds * config.disruption_time_multiplier
    
    effective_duration = max(0, session_duration - micro_penalty - disruption_penalty)
    stability_score = min(1.0, effective_duration / session_duration) if session_duration > 0 else 0.0
    
    # Bitrate efficiency
    bitrate_efficiency = (
        stream_data.actual_avg_bitrate_kbps / stream_data.target_bitrate_kbps 
        if stream_data.target_bitrate_kbps > 0 else 0.0
    )
    
    # Supporter efficiency from P2P data
    supporter_efficiency = p2p_data.data_efficiency_score if p2p_data else 0.8
    
    return SessionAnalytics(
        stability_score=stability_score,
        bitrate_efficiency=bitrate_efficiency,
        supporter_efficiency=supporter_efficiency
    )
```

### **Database Schema for Analytics**

```sql
CREATE TABLE broadcast_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    broadcast_id UUID REFERENCES broadcasts(id),
    session_duration_seconds INTEGER NOT NULL,
    stability_score FLOAT NOT NULL,
    bitrate_efficiency FLOAT NOT NULL,
    supporter_efficiency FLOAT NOT NULL,
    raw_stream_data JSONB,
    raw_p2p_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(broadcast_id)  -- One analytics record per broadcast
);

-- Reconciliation job support
CREATE INDEX idx_broadcasts_missing_analytics ON broadcasts(status, offline_at) 
WHERE status = 'OFFLINE';
```

---

## 🎛️ Phase 4: Smart Supporter Allocation (Week 4)

### **Historical Performance Integration**

```python
# Enhanced coordinator allocation logic
@app.post("/broadcasts/{broadcast_id}/allocate-supporters")
async def allocate_supporters(
    broadcast_id: UUID,
    db: Session = Depends(get_db)
):
    """AI-driven supporter node allocation"""
    broadcast = get_broadcast_or_404(db, broadcast_id)
    profile = broadcast.ingest_profile
    
    # Base allocation from historical data
    base_nodes = profile.avg_supporter_nodes_required or 5
    
    # Reliability multiplier
    if profile.stability_score > 0.95:
        reliability_bonus = 1.2  # Excellent streams get premium support
    elif profile.stability_score > 0.8:
        reliability_bonus = 1.0  # Normal allocation
    else:
        reliability_bonus = 0.8  # Problematic streams get reduced allocation
    
    # Target bitrate considerations
    bitrate_factor = min(2.0, profile.target_bitrate_kbps / 2000)  # Scale with bitrate
    
    target_nodes = int(base_nodes * reliability_bonus * bitrate_factor)
    target_nodes = max(2, min(target_nodes, 20))  # Reasonable bounds
    
    # Allocate actual supporter nodes
    allocated_nodes = assign_supporter_nodes(broadcast_id, target_nodes)
    
    return {
        "broadcast_id": broadcast_id,
        "target_nodes": target_nodes,
        "allocated_nodes": len(allocated_nodes),
        "allocation_reasoning": {
            "base_nodes": base_nodes,
            "stability_score": profile.stability_score,
            "reliability_bonus": reliability_bonus,
            "bitrate_factor": bitrate_factor
        }
    }

def assign_supporter_nodes(broadcast_id: UUID, target_count: int):
    """Assign best available supporter nodes to broadcast"""
    # Get available nodes sorted by performance
    available_nodes = db.query(models.Node).filter(
        models.Node.status == 'active',
        models.Node.current_stream_id.is_(None)
    ).order_by(
        models.Node.uptime_percentage.desc(),
        models.Node.bandwidth_mbps.desc()
    ).limit(target_count).all()
    
    # Assign nodes to broadcast
    for node in available_nodes:
        node.current_stream_id = broadcast_id
        node.assignment_timestamp = datetime.utcnow()
    
    db.commit()
    return available_nodes
```

---

## 🧪 Testing & Validation Plan

### **Unit Tests**

```python
# tests/test_lifecycle.py
def test_state_transitions():
    """Test valid/invalid state transitions"""
    stream = create_test_stream(status='READY')
    
    # Valid transitions
    assert update_stream_status(stream.id, 'TESTING') == 200
    assert update_stream_status(stream.id, 'LIVE') == 200
    assert update_stream_status(stream.id, 'OFFLINE') == 200
    
    # Invalid transitions
    assert update_stream_status(stream.id, 'TESTING') == 400  # Can't test when offline

def test_heartbeat_detection():
    """Test automatic offline detection"""
    stream = create_test_stream(status='LIVE')
    
    # Simulate heartbeat expiry
    redis_client.delete(f"stream:health:{stream.stream_id}")
    
    # Run reaper worker
    reaper_worker()
    
    # Verify status updated
    updated_stream = db.get(models.Stream, stream.id)
    assert updated_stream.status == 'OFFLINE'
    assert updated_stream.offline_at is not None

def test_analytics_calculation():
    """Test session analytics accuracy"""
    stream_data = StreamSessionSummary(
        broadcast_id="test-123",
        session_start_ts=1000,
        session_end_ts=4000,  # 50 minutes
        micro_disconnects=2,
        micro_disconnect_total_seconds=30
    )
    
    analytics = calculate_session_metrics(stream_data, None)
    
    # Stability score should account for penalties
    expected_score = (3000 - 20 - 60) / 3000  # Duration - micro penalties - disruption penalties
    assert abs(analytics.stability_score - expected_score) < 0.01
```

### **Integration Tests**

```bash
# tests/integration_test.sh
#!/bin/bash

# 1. Create ingest profile
PROFILE_ID=$(curl -s -X POST "http://localhost:8000/ingest-profiles" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Setup", "target_bitrate_kbps": 2500}' | jq -r '.id')

# 2. Create broadcast
BROADCAST_ID=$(curl -s -X POST "http://localhost:8000/broadcasts" \
  -H "Content-Type: application/json" \
  -d "{\"ingest_profile_id\": \"$PROFILE_ID\", \"title\": \"Test Stream\"}" | jq -r '.id')

# 3. Test state transitions
curl -X PATCH "http://localhost:8000/streams/$BROADCAST_ID/status" \
  -d '{"status": "LIVE"}'

# 4. Simulate heartbeat
STREAM_KEY=$(curl -s "http://localhost:8000/broadcasts/$BROADCAST_ID" | jq -r '.stream_id')
redis-cli SETEX "stream:health:$STREAM_KEY" 60 "LIVE"

# 5. Test supporter allocation
curl -X POST "http://localhost:8000/broadcasts/$BROADCAST_ID/allocate-supporters"

# 6. Test analytics endpoint
curl "http://localhost:8000/ingest-profiles/$PROFILE_ID/analytics"

echo "✅ Integration tests completed"
```

---

## 🚀 Deployment Plan

### **Week 1: Core State Machine**
- [ ] Database migrations for status fields
- [ ] API endpoints for manual transitions
- [ ] Heartbeat system with Redis
- [ ] Reaper worker deployment
- [ ] Clean up stale `obs-test` stream

### **Week 2: Architecture Separation**  
- [ ] IngestProfile and Broadcast tables
- [ ] Data migration from existing streams
- [ ] Enhanced API endpoints
- [ ] Profile analytics endpoints

### **Week 3: Analytics Pipeline**
- [ ] Session summary events from ingest server
- [ ] Analytics processing worker
- [ ] BroadcastAnalytics table
- [ ] Profile aggregate calculations

### **Week 4: Smart Allocation**
- [ ] Historical performance integration
- [ ] AI-driven supporter allocation
- [ ] Performance-based node assignment
- [ ] Comprehensive testing

### **Friend Testing Integration**
- [ ] Update `scripts/setup-node.sh` to use live stream discovery
- [ ] Create streamer dashboard showing real-time analytics
- [ ] Add manual start/stop controls for broadcasts
- [ ] Performance feedback for supporters

---

## 📊 Success Metrics

### **Technical Metrics**
- **State Accuracy**: >99% correct status transitions
- **Heartbeat Reliability**: <5 second detection latency for offline streams
- **Analytics Completeness**: >95% of broadcasts have analytics records
- **API Performance**: <200ms response time for all endpoints

### **User Experience Metrics**
- **Streamer Satisfaction**: 8/10+ on setup ease and reliability feedback
- **Supporter Confidence**: >90% uptime on allocated nodes
- **System Reliability**: <1% false positive offline detections

### **Business Metrics**
- **Stream Quality**: Average stability score >0.85
- **Resource Efficiency**: <10% over-allocation of supporter nodes
- **Friend Retention**: >80% of test friends continue using platform

---

## 🔧 Technical Debt & Future Enhancements

### **Phase 5+ Considerations**
- **WebSocket Real-time Updates**: Replace polling with live status updates
- **Advanced Analytics Dashboard**: Grafana integration for operations
- **Multi-Region Support**: Geo-distributed ingest servers
- **Machine Learning**: Predictive supporter allocation based on content type
- **Blockchain Integration**: Immutable audit trail for earnings/performance

### **Security Considerations**
- **Stream Key Rotation**: Automatic rotation for security
- **RTMP Authentication**: Validate stream keys before accepting connections
- **Rate Limiting**: Prevent abuse of status change endpoints
- **Audit Logging**: Complete audit trail for all state changes

---

**🎯 READY FOR IMPLEMENTATION: This plan transforms StreamrP2P from basic stream management to enterprise-grade lifecycle orchestration while maintaining simplicity for friends testing.** 