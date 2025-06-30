from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum
from decimal import Decimal

class StreamStatus(str, Enum):
    READY = "READY"
    TESTING = "TESTING" 
    LIVE = "LIVE"
    OFFLINE = "OFFLINE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"

class StreamStatusFilter(str, Enum):
    ALL = "ALL"
    READY = "READY"
    TESTING = "TESTING"
    LIVE = "LIVE"
    OFFLINE = "OFFLINE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"

class StreamCreate(BaseModel):
    stream_id: str
    sponsor_address: str
    token_balance: float
    rtmp_url: str

class StreamResponse(BaseModel):
    id: int
    stream_id: str
    sponsor_address: str
    token_balance: float
    rtmp_url: str
    status: str
    created_at: datetime
    
    # Lifecycle timestamps
    live_started_at: Optional[datetime] = None
    offline_at: Optional[datetime] = None
    testing_started_at: Optional[datetime] = None
    stale_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class StreamStatusUpdate(BaseModel):
    status: StreamStatus

class NodeHeartbeat(BaseModel):
    node_id: str
    stream_id: str
    stats_url: str
    timestamp: datetime = datetime.utcnow()

class NodeResponse(BaseModel):
    id: int
    node_id: str
    stream_id: str
    stats_url: str
    last_heartbeat: datetime
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProbeResultCreate(BaseModel):
    stream_id: str
    node_id: str
    probe_type: str
    success: bool
    response_data: Optional[str] = None
    error_message: Optional[str] = None

class ProbeResultResponse(BaseModel):
    id: int
    stream_id: str
    node_id: str
    probe_type: str
    success: bool
    response_data: Optional[str]
    error_message: Optional[str]
    probe_timestamp: datetime
    
    class Config:
        from_attributes = True

# Economic Validation Schemas

class BandwidthReport(BaseModel):
    session_id: str
    bytes_transferred: int
    start_interval: datetime
    end_interval: datetime
    source_bitrate_kbps: Optional[int] = None

class BandwidthReportResponse(BaseModel):
    id: int
    session_id: str
    reporting_node_id: str
    bytes_transferred: int
    report_timestamp: datetime
    start_interval: datetime
    end_interval: datetime
    source_bitrate_kbps: Optional[int]
    is_verified: bool
    trust_score: Optional[Decimal]
    verification_notes: Optional[str]
    
    class Config:
        from_attributes = True

class UserAccountResponse(BaseModel):
    user_id: str
    balance_usd: Decimal
    total_gb_relayed: Decimal
    earnings_last_30d: Decimal
    trust_score: Decimal
    flags: Optional[List[str]]
    last_updated_at: datetime
    
    class Config:
        from_attributes = True

class EconomicsDashboard(BaseModel):
    active_sessions: int
    total_nodes: int
    total_gb_delivered_24h: Decimal
    platform_margin_percent: Decimal
    avg_creator_revenue_share: Decimal
    qualified_earners_count: int
    top_earners: List[dict]
    suspicious_activity: List[dict]

class NodeEconomics(BaseModel):
    node_id: str
    balance_usd: Decimal
    earnings_last_30d: Decimal
    gb_relayed: Decimal
    trust_score: Decimal
    hourly_earnings: List[dict] 