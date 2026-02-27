"""Add performance indexes for query optimization.

Revision ID: 003
Revises: 002
Create Date: 2025-01-03 00:00:00.000000+00:00

Adds indexes on frequently queried columns:
  - bandwidth_ledger.session_id
  - bandwidth_ledger.reporting_node_id
  - bandwidth_ledger.report_timestamp
  - nodes.stream_id
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_bandwidth_ledger_session_id",
        "bandwidth_ledger",
        ["session_id"],
    )
    op.create_index(
        "ix_bandwidth_ledger_reporting_node_id",
        "bandwidth_ledger",
        ["reporting_node_id"],
    )
    op.create_index(
        "ix_bandwidth_ledger_report_timestamp",
        "bandwidth_ledger",
        ["report_timestamp"],
    )
    op.create_index(
        "ix_nodes_stream_id",
        "nodes",
        ["stream_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_nodes_stream_id", table_name="nodes")
    op.drop_index("ix_bandwidth_ledger_report_timestamp", table_name="bandwidth_ledger")
    op.drop_index("ix_bandwidth_ledger_reporting_node_id", table_name="bandwidth_ledger")
    op.drop_index("ix_bandwidth_ledger_session_id", table_name="bandwidth_ledger")
