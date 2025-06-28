from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Stream(Base):
    __tablename__ = "streams"
    
    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(String, unique=True, index=True, nullable=False)
    sponsor_address = Column(String, nullable=False)
    token_balance = Column(Float, default=0.0)
    rtmp_url = Column(String, nullable=False)
    status = Column(String, default="READY")  # READY, TESTING, LIVE, OFFLINE, STALE, ARCHIVED
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Lifecycle timestamps
    live_started_at = Column(DateTime)
    offline_at = Column(DateTime)
    testing_started_at = Column(DateTime)
    stale_at = Column(DateTime)
    archived_at = Column(DateTime)
    
    # Relationships
    nodes = relationship("Node", back_populates="stream")
    probe_results = relationship("ProbeResult", back_populates="stream")

class Node(Base):
    __tablename__ = "nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, nullable=False, unique=True, index=True)
    stream_id = Column(String, ForeignKey("streams.stream_id"), nullable=False)
    stats_url = Column(String, nullable=False)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # active, inactive, flagged
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stream = relationship("Stream", back_populates="nodes")
    probe_results = relationship("ProbeResult", back_populates="node")

class ProbeResult(Base):
    __tablename__ = "probe_results"
    
    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(String, ForeignKey("streams.stream_id"), nullable=False)
    node_id = Column(String, ForeignKey("nodes.node_id"), nullable=False, index=True)
    probe_type = Column(String, nullable=False)  # stats_poll, spot_check
    success = Column(Boolean, nullable=False)
    response_data = Column(Text)  # JSON response from stats endpoint
    error_message = Column(Text)
    probe_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stream = relationship("Stream", back_populates="probe_results")
    node = relationship("Node", back_populates="probe_results") 