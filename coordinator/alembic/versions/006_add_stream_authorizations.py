"""Add stream_authorizations table.

Revision ID: 006
Revises: 005
Create Date: 2026-02-28 14:00:00.000000+00:00

The StreamAuthorization model exists in models.py but no prior migration
created the table, causing 500 errors on any code path that touches it.
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stream_authorizations",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "stream_id",
            sa.String(),
            sa.ForeignKey("streams.stream_id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("user_identities.user_id"),
            nullable=False,
        ),
        sa.Column("authorized_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("authorized_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("stream_id", "user_id", name="uq_stream_user_auth"),
    )
    op.create_index(
        "ix_stream_authorizations_stream_id",
        "stream_authorizations",
        ["stream_id"],
    )
    op.create_index(
        "ix_stream_authorizations_user_id",
        "stream_authorizations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("stream_authorizations")
