from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List, Literal
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

# --- User Identity Schemas ---

class UserIdentityCreate(BaseModel):
    display_name: str
    email: Optional[str] = None
    password: Optional[str] = None  # for streamer registration

class UserIdentityResponse(BaseModel):
    user_id: str
    display_name: str
    email: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Stream Schemas ---

class StreamCreate(BaseModel):
    stream_id: str
    rtmp_url: str

class StreamCreateResponse(BaseModel):
    id: int
    stream_id: str
    stream_key: str
    owner_user_id: str
    rtmp_url: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class StreamResponse(BaseModel):
    id: int
    stream_id: str
    owner_user_id: str
    stream_key: str
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

# --- Node Schemas ---

class NodeHeartbeat(BaseModel):
    node_id: str
    stream_id: str
    stats_url: str
    vpn_ip: Optional[str] = None
    capacity_pct: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

# --- Probe Result Schemas ---

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
    response_data: Optional[str] = None
    error_message: Optional[str] = None
    probe_timestamp: datetime
    
    class Config:
        from_attributes = True

# --- Bandwidth Report Schemas ---

class BandwidthReport(BaseModel):
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
    source_bitrate_kbps: Optional[int] = None
    is_verified: bool
    trust_score: Optional[Decimal] = None
    verification_notes: Optional[str] = None
    
    class Config:
        from_attributes = True

# --- Feedback Schemas ---

class FeedbackCreate(BaseModel):
    text: str
    category: Optional[Literal["bug", "suggestion", "praise"]] = None
    node_id: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    text: str
    category: Optional[str] = None
    node_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Payout / Earnings Schemas ---

class PayoutLogEntryResponse(BaseModel):
    timestamp: datetime
    bytes_relayed: int
    earnings_usd: str  # Decimal as string
    trust_score: str  # Decimal as string
    penalty_applied: bool

    class Config:
        from_attributes = True

class EarningsResponse(BaseModel):
    node_id: str
    period: dict  # {"start": datetime, "end": datetime}
    total_earnings_usd: str
    entries: List[PayoutLogEntryResponse]

# --- Economic Dashboard Schemas ---

class UserAccountResponse(BaseModel):
    user_id: str
    balance_usd: Decimal
    total_gb_relayed: Decimal
    earnings_last_30d: Decimal
    trust_score: Decimal
    flags: Optional[List[str]] = None
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
