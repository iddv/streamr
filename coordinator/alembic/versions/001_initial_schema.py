"""Initial schema — captures existing 5-table layout.

Revision ID: 001
Revises: —
Create Date: 2025-01-01 00:00:00.000000+00:00

Tables: streams, nodes, probe_results, bandwidth_ledger, user_accounts
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if tables already exist (e.g. created by legacy create_all()).
    # If so, skip creation — the schema is already in place.
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'streams')"
        )
    )
    tables_exist = result.scalar()
    if tables_exist:
        # Tables already created by legacy code — nothing to do.
        return

    # --- streams ---
    op.create_table(
        "streams",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("stream_id", sa.String(), unique=True, index=True, nullable=False),
        sa.Column("sponsor_address", sa.String(), nullable=False),
        sa.Column("token_balance", sa.Float(), server_default="0.0"),
        sa.Column("rtmp_url", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="READY"),
        sa.Column("created_at", sa.DateTime()),
        # Lifecycle timestamps
        sa.Column("live_started_at", sa.DateTime()),
        sa.Column("offline_at", sa.DateTime()),
        sa.Column("testing_started_at", sa.DateTime()),
        sa.Column("stale_at", sa.DateTime()),
        sa.Column("archived_at", sa.DateTime()),
        # Economic tracking
        sa.Column("total_gb_delivered", sa.Numeric(12, 4), server_default="0.00"),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), server_default="0.00"),
        sa.Column("platform_fee_usd", sa.Numeric(10, 4), server_default="0.00"),
        sa.Column("creator_payout_usd", sa.Numeric(10, 4), server_default="0.00"),
    )

    # --- nodes ---
    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("node_id", sa.String(), unique=True, index=True, nullable=False),
        sa.Column(
            "stream_id",
            sa.String(),
            sa.ForeignKey("streams.stream_id"),
            nullable=False,
        ),
        sa.Column("stats_url", sa.String(), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime()),
        sa.Column("status", sa.String(), server_default="active"),
        sa.Column("created_at", sa.DateTime()),
    )

    # --- probe_results ---
    op.create_table(
        "probe_results",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "stream_id",
            sa.String(),
            sa.ForeignKey("streams.stream_id"),
            nullable=False,
        ),
        sa.Column(
            "node_id",
            sa.String(),
            sa.ForeignKey("nodes.node_id"),
            nullable=False,
            index=True,
        ),
        sa.Column("probe_type", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("response_data", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("probe_timestamp", sa.DateTime()),
    )

    # --- bandwidth_ledger ---
    op.create_table(
        "bandwidth_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True, index=True),
        sa.Column(
            "session_id",
            sa.String(255),
            sa.ForeignKey("streams.stream_id"),
            nullable=False,
        ),
        sa.Column(
            "reporting_node_id",
            sa.String(255),
            sa.ForeignKey("nodes.node_id"),
            nullable=False,
        ),
        sa.Column("bytes_transferred", sa.BigInteger(), nullable=False),
        sa.Column("report_timestamp", sa.DateTime(), nullable=False),
        sa.Column("start_interval", sa.DateTime(), nullable=False),
        sa.Column("end_interval", sa.DateTime(), nullable=False),
        sa.Column("source_bitrate_kbps", sa.Integer()),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("trust_score", sa.Numeric(3, 2)),
        sa.Column("verification_notes", sa.Text()),
    )

    # --- user_accounts ---
    op.create_table(
        "user_accounts",
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("nodes.node_id"),
            primary_key=True,
        ),
        sa.Column(
            "balance_usd", sa.Numeric(10, 4), server_default="0.00", nullable=False
        ),
        sa.Column(
            "total_gb_relayed",
            sa.Numeric(12, 4),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "earnings_last_30d",
            sa.Numeric(10, 4),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "trust_score", sa.Numeric(3, 2), server_default="1.00", nullable=False
        ),
        sa.Column("flags", sa.ARRAY(sa.String())),
        sa.Column("last_updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_accounts")
    op.drop_table("bandwidth_ledger")
    op.drop_table("probe_results")
    op.drop_table("nodes")
    op.drop_table("streams")
