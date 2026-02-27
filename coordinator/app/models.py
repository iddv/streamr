from uuid import uuid4

from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, Text, ForeignKey, BigInteger, Numeric, ARRAY, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()


class UserIdentity(Base):
    __tablename__ = "user_identities"

    user_id = Column(String(255), primary_key=True, default=lambda: str(uuid4()))
    display_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)  # nullable for node-only users
    role = Column(String(20), default="node")  # "streamer" or "node"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships (forward-looking — FK columns on Node/UserAccount added in Task 1.5/1.6)
    nodes = relationship("Node", back_populates="user_identity", foreign_keys="[Node.user_id]")
    account = relationship("UserAccount", back_populates="user_identity", uselist=False, foreign_keys="[UserAccount.user_id]")
    authorizations = relationship("StreamAuthorization", back_populates="user_identity")


class Stream(Base):
    __tablename__ = "streams"
    
    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(String, unique=True, index=True, nullable=False)
    owner_user_id = Column(String(255), ForeignKey("user_identities.user_id"), nullable=False)
    stream_key = Column(String(64), nullable=False, index=True)
    rtmp_url = Column(String, nullable=False)
    status = Column(String, default="READY")  # READY, TESTING, LIVE, OFFLINE, STALE, ARCHIVED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
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
    owner = relationship("UserIdentity", backref="owned_streams")
    nodes = relationship("Node", back_populates="stream")
    probe_results = relationship("ProbeResult", back_populates="stream")
    bandwidth_reports = relationship("BandwidthLedger", back_populates="stream")


class StreamAuthorization(Base):
    __tablename__ = "stream_authorizations"
    __table_args__ = (
        UniqueConstraint("stream_id", "user_id", name="uq_stream_user_auth"),
    )

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(String, ForeignKey("streams.stream_id"), nullable=False)
    user_id = Column(String(255), ForeignKey("user_identities.user_id"), nullable=False)
    authorized_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    authorized_by = Column(String(255))  # user_id of the streamer who authorized

    # Relationships
    stream = relationship("Stream", backref="authorizations")
    user_identity = relationship("UserIdentity", back_populates="authorizations")


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        UniqueConstraint("node_id", "stream_id", name="uq_node_stream"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, nullable=False, index=True)
    stream_id = Column(String, ForeignKey("streams.stream_id"), nullable=False)
    user_id = Column(String(255), ForeignKey("user_identities.user_id"), nullable=False)
    stats_url = Column(String, nullable=False)
    vpn_ip = Column(String(45))  # IPv4 or IPv6
    capacity_pct = Column(Integer, default=0)
    last_heartbeat = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="active")  # active, inactive, flagged
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    stream = relationship("Stream", back_populates="nodes")
    user_identity = relationship("UserIdentity", back_populates="nodes")
    probe_results = relationship("ProbeResult", back_populates="node",
                                foreign_keys="[ProbeResult.node_id]",
                                primaryjoin="Node.node_id == ProbeResult.node_id")
    user_account = relationship("UserAccount", back_populates="node", uselist=False,
                                foreign_keys="[UserAccount.user_id]",
                                primaryjoin="Node.user_id == UserAccount.user_id")
    bandwidth_reports = relationship("BandwidthLedger", back_populates="reporting_node",
                                     foreign_keys="[BandwidthLedger.reporting_node_id]",
                                     primaryjoin="Node.node_id == BandwidthLedger.reporting_node_id")

class ProbeResult(Base):
    __tablename__ = "probe_results"
    
    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(String, ForeignKey("streams.stream_id"), nullable=False)
    node_id = Column(String, nullable=False, index=True)  # logical ref to nodes.node_id (not FK — node_id no longer unique)
    probe_type = Column(String, nullable=False)  # stats_poll, spot_check
    success = Column(Boolean, nullable=False)
    response_data = Column(Text)  # JSON response from stats endpoint
    error_message = Column(Text)
    probe_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    stream = relationship("Stream", back_populates="probe_results")
    node = relationship("Node", back_populates="probe_results",
                        foreign_keys="[ProbeResult.node_id]",
                        primaryjoin="ProbeResult.node_id == Node.node_id")

# Economic Validation Models

class BandwidthLedger(Base):
    __tablename__ = "bandwidth_ledger"
    
    id = Column(BigInteger, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("streams.stream_id"), nullable=False)
    reporting_node_id = Column(String(255), nullable=False)  # logical ref to nodes.node_id (not FK — node_id no longer unique)
    bytes_transferred = Column(BigInteger, nullable=False)
    report_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    start_interval = Column(DateTime, nullable=False)
    end_interval = Column(DateTime, nullable=False)
    source_bitrate_kbps = Column(Integer)
    is_verified = Column(Boolean, default=False, nullable=False)
    trust_score = Column(Numeric(3, 2))  # 0.00-1.00
    verification_notes = Column(Text)
    
    # Relationships
    stream = relationship("Stream", back_populates="bandwidth_reports")
    reporting_node = relationship("Node", back_populates="bandwidth_reports",
                                  foreign_keys="[BandwidthLedger.reporting_node_id]",
                                  primaryjoin="BandwidthLedger.reporting_node_id == Node.node_id")

class UserAccount(Base):
    __tablename__ = "user_accounts"
    
    user_id = Column(String(255), ForeignKey("user_identities.user_id"), primary_key=True)
    balance_usd = Column(Numeric(10, 4), default=0.00, nullable=False)
    total_gb_relayed = Column(Numeric(12, 4), default=0.00, nullable=False)
    earnings_last_30d = Column(Numeric(10, 4), default=0.00, nullable=False)
    trust_score = Column(Numeric(3, 2), default=1.00, nullable=False)
    flags = Column(ARRAY(String))  # ['suspicious_reporting', 'high_variance']
    last_updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user_identity = relationship("UserIdentity", back_populates="account")
    node = relationship("Node", back_populates="user_account", uselist=False,
                        foreign_keys="[Node.user_id]",
                        primaryjoin="UserAccount.user_id == Node.user_id")


# --- Feedback, Payout, and Data Retention Models (Migration 004) ---


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    category = Column(String(20), nullable=True)  # "bug", "suggestion", "praise"
    node_id = Column(String, nullable=True)  # optional, for follow-up
    user_id = Column(String(255), ForeignKey("user_identities.user_id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user_identity = relationship("UserIdentity", backref="feedback")


class PayoutLog(Base):
    __tablename__ = "payout_log"

    id = Column(Integer, primary_key=True, index=True)
    cycle_timestamp = Column(DateTime, nullable=False)
    total_amount_usd = Column(Numeric(10, 4), nullable=False)
    total_bytes_processed = Column(BigInteger, nullable=False)
    nodes_paid = Column(Integer, nullable=False)
    penalties_applied = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

    # Relationships
    entries = relationship("PayoutLogEntry", back_populates="payout_log")


class PayoutLogEntry(Base):
    __tablename__ = "payout_log_entries"

    id = Column(BigInteger, primary_key=True, index=True)
    payout_log_id = Column(Integer, ForeignKey("payout_log.id"), nullable=False)
    node_id = Column(String, nullable=False)  # logical ref
    user_id = Column(String(255), ForeignKey("user_identities.user_id"), nullable=False)
    bytes_relayed = Column(BigInteger, nullable=False)
    earnings_usd = Column(Numeric(10, 4), nullable=False)
    trust_score = Column(Numeric(3, 2), nullable=False)
    penalty_applied = Column(Boolean, default=False)
    timestamp = Column(DateTime, nullable=False)

    # Relationships
    payout_log = relationship("PayoutLog", back_populates="entries")
    user_identity = relationship("UserIdentity", backref="payout_entries")


class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"
    __table_args__ = (
        UniqueConstraint("node_id", "month", name="uq_monthly_summary_node_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, nullable=False)
    user_id = Column(String(255), ForeignKey("user_identities.user_id"), nullable=False)
    month = Column(Date, nullable=False)  # first day of the month
    total_bytes = Column(BigInteger, nullable=False)
    verified_bytes = Column(BigInteger, nullable=False)
    avg_trust_score = Column(Numeric(3, 2), nullable=False)
    total_reports = Column(Integer, nullable=False)

    # Relationships
    user_identity = relationship("UserIdentity", backref="monthly_summaries")
