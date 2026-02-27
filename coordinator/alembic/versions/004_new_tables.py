"""Add feedback, payout_log, payout_log_entries, monthly_summaries tables.

Revision ID: 004
Revises: 003
Create Date: 2025-01-04 00:00:00.000000+00:00

New tables:
  - feedback: anonymous user feedback (Req 24, Design §26)
  - payout_log: hourly payout cycle summaries (Req 15, Design §18)
  - payout_log_entries: per-node payout details (Req 15, Design §19)
  - monthly_summaries: aggregated data retention (Req 3c, Design §6)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- feedback ---
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(20), nullable=True),  # bug, suggestion, praise
        sa.Column("node_id", sa.String(), nullable=True),  # optional, for follow-up
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("user_identities.user_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- payout_log ---
    op.create_table(
        "payout_log",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("cycle_timestamp", sa.DateTime(), nullable=False),
        sa.Column("total_amount_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("total_bytes_processed", sa.BigInteger(), nullable=False),
        sa.Column("nodes_paid", sa.Integer(), nullable=False),
        sa.Column("penalties_applied", sa.Integer(), server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # --- payout_log_entries ---
    op.create_table(
        "payout_log_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, index=True),
        sa.Column(
            "payout_log_id",
            sa.Integer(),
            sa.ForeignKey("payout_log.id"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(), nullable=False),  # logical ref
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("user_identities.user_id"),
            nullable=False,
        ),
        sa.Column("bytes_relayed", sa.BigInteger(), nullable=False),
        sa.Column("earnings_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("trust_score", sa.Numeric(3, 2), nullable=False),
        sa.Column("penalty_applied", sa.Boolean(), server_default="false"),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_payout_log_entries_payout_log_id",
        "payout_log_entries",
        ["payout_log_id"],
    )
    op.create_index(
        "ix_payout_log_entries_user_id",
        "payout_log_entries",
        ["user_id"],
    )

    # --- monthly_summaries ---
    op.create_table(
        "monthly_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("user_identities.user_id"),
            nullable=False,
        ),
        sa.Column("month", sa.Date(), nullable=False),  # first day of the month
        sa.Column("total_bytes", sa.BigInteger(), nullable=False),
        sa.Column("verified_bytes", sa.BigInteger(), nullable=False),
        sa.Column("avg_trust_score", sa.Numeric(3, 2), nullable=False),
        sa.Column("total_reports", sa.Integer(), nullable=False),
        sa.UniqueConstraint("node_id", "month", name="uq_monthly_summary_node_month"),
    )


def downgrade() -> None:
    op.drop_table("monthly_summaries")
    op.drop_table("payout_log_entries")
    op.drop_table("payout_log")
    op.drop_table("feedback")
