"""Add missing vpn_ip and capacity_pct columns to nodes table.

Revision ID: 005
Revises: 004
Create Date: 2026-02-27 22:30:00.000000+00:00

The ORM model defines vpn_ip and capacity_pct on the Node class but no
prior migration created these columns.  This migration adds them.
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nodes", sa.Column("vpn_ip", sa.String(45), nullable=True))
    op.add_column("nodes", sa.Column("capacity_pct", sa.Integer(), server_default="0"))


def downgrade() -> None:
    op.drop_column("nodes", "capacity_pct")
    op.drop_column("nodes", "vpn_ip")
