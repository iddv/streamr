from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, BigInteger, Numeric, ARRAY
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
    
    # Economic tracking columns
    total_gb_delivered = Column(Numeric(12, 4), default=0.00)
    total_cost_usd = Column(Numeric(10, 4), default=0.00)
    platform_fee_usd = Column(Numeric(10, 4), default=0.00)
    creator_payout_usd = Column(Numeric(10, 4), default=0.00)
    
    # Relationships
    nodes = relationship("Node", back_populates="stream")
    probe_results = relationship("ProbeResult", back_populates="stream")
    bandwidth_reports = relationship("BandwidthLedger", back_populates="stream")

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
    user_account = relationship("UserAccount", back_populates="node", uselist=False)
    bandwidth_reports = relationship("BandwidthLedger", back_populates="reporting_node")

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

# Economic Validation Models

class BandwidthLedger(Base):
    __tablename__ = "bandwidth_ledger"
    
    id = Column(BigInteger, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("streams.stream_id"), nullable=False)
    reporting_node_id = Column(String(255), ForeignKey("nodes.node_id"), nullable=False)
    bytes_transferred = Column(BigInteger, nullable=False)
    report_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    start_interval = Column(DateTime, nullable=False)
    end_interval = Column(DateTime, nullable=False)
    source_bitrate_kbps = Column(Integer)
    is_verified = Column(Boolean, default=False, nullable=False)
    trust_score = Column(Numeric(3, 2))  # 0.00-1.00
    verification_notes = Column(Text)
    
    # Relationships
    stream = relationship("Stream", back_populates="bandwidth_reports")
    reporting_node = relationship("Node", back_populates="bandwidth_reports")

class UserAccount(Base):
    __tablename__ = "user_accounts"
    
    user_id = Column(String(255), ForeignKey("nodes.node_id"), primary_key=True)
    balance_usd = Column(Numeric(10, 4), default=0.00, nullable=False)
    total_gb_relayed = Column(Numeric(12, 4), default=0.00, nullable=False)
    earnings_last_30d = Column(Numeric(10, 4), default=0.00, nullable=False)
    trust_score = Column(Numeric(3, 2), default=1.00, nullable=False)
    flags = Column(ARRAY(String))  # ['suspicious_reporting', 'high_variance']
    last_updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    node = relationship("Node", back_populates="user_account") 