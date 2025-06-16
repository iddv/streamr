from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

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
    
    class Config:
        from_attributes = True

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