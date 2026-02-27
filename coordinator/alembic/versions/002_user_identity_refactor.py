"""User identity refactor — decouple users from nodes.

Revision ID: 002
Revises: 001
Create Date: 2025-01-02 00:00:00.000000+00:00

Steps:
  1. Create user_identities table
  2. Migrate existing UserAccount records into user_identities
  3. Add user_id FK to nodes, populate from user_accounts
  4. Change nodes.node_id from unique to composite unique (node_id, stream_id)
  5. Re-link user_accounts.user_id FK from nodes.node_id to user_identities.user_id
  6. Archive and drop deprecated sponsor_address/token_balance from streams
  7. Add owner_user_id FK and stream_key columns to streams
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # Step 1: Create user_identities table
    # ---------------------------------------------------------------
    op.create_table(
        "user_identities",
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), server_default="node"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_user_identities_email", "user_identities", ["email"], unique=True)

    # ---------------------------------------------------------------
    # Step 2: Migrate existing UserAccount records → UserIdentity
    #
    # For each user_accounts row, create a user_identities row using
    # the existing user_id (which currently references nodes.node_id)
    # as the basis for a new UUID-based user_id.
    # We store the mapping so we can re-link FKs later.
    # ---------------------------------------------------------------
    conn = op.get_bind()

    existing_accounts = conn.execute(
        sa.text("SELECT user_id FROM user_accounts")
    ).fetchall()

    # Map: old node_id (user_accounts.user_id) → new user_identity.user_id
    node_to_identity = {}
    for (old_node_id,) in existing_accounts:
        new_user_id = str(uuid4())
        node_to_identity[old_node_id] = new_user_id
        conn.execute(
            sa.text(
                "INSERT INTO user_identities (user_id, display_name, role, created_at) "
                "VALUES (:uid, :name, 'node', NOW())"
            ),
            {"uid": new_user_id, "name": old_node_id},
        )

    # ---------------------------------------------------------------
    # Step 3: Add user_id FK column to nodes, populate from mapping
    # ---------------------------------------------------------------
    op.add_column(
        "nodes",
        sa.Column("user_id", sa.String(255), nullable=True),
    )

    # Populate nodes.user_id from the mapping (node_id → identity user_id)
    for old_node_id, new_user_id in node_to_identity.items():
        conn.execute(
            sa.text(
                "UPDATE nodes SET user_id = :uid WHERE node_id = :nid"
            ),
            {"uid": new_user_id, "nid": old_node_id},
        )

    # For any nodes without a matching user_account, create an identity
    orphan_nodes = conn.execute(
        sa.text("SELECT DISTINCT node_id FROM nodes WHERE user_id IS NULL")
    ).fetchall()
    for (node_id,) in orphan_nodes:
        new_user_id = str(uuid4())
        node_to_identity[node_id] = new_user_id
        conn.execute(
            sa.text(
                "INSERT INTO user_identities (user_id, display_name, role, created_at) "
                "VALUES (:uid, :name, 'node', NOW())"
            ),
            {"uid": new_user_id, "name": node_id},
        )
        conn.execute(
            sa.text("UPDATE nodes SET user_id = :uid WHERE node_id = :nid"),
            {"uid": new_user_id, "nid": node_id},
        )

    # Now make user_id NOT NULL and add FK
    op.alter_column("nodes", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_nodes_user_id",
        "nodes",
        "user_identities",
        ["user_id"],
        ["user_id"],
    )

    # ---------------------------------------------------------------
    # Step 4: Change nodes.node_id unique → composite (node_id, stream_id)
    # ---------------------------------------------------------------
    # Drop existing unique constraint on node_id.
    # The 001 migration created it via unique=True on the Column, which
    # in PostgreSQL produces a unique index named "ix_nodes_node_id" or
    # a constraint. We drop the index that backs the unique constraint.
    op.drop_index("ix_nodes_node_id", table_name="nodes")

    # Also need to handle FKs that reference nodes.node_id before we
    # can drop its uniqueness. The referencing tables are:
    #   - probe_results.node_id → nodes.node_id
    #   - bandwidth_ledger.reporting_node_id → nodes.node_id
    #   - user_accounts.user_id → nodes.node_id
    # We'll drop these FKs, change the constraint, then re-create them
    # pointing to user_identities where appropriate.

    # Drop FKs referencing nodes.node_id
    op.drop_constraint(
        "probe_results_node_id_fkey", "probe_results", type_="foreignkey"
    )
    op.drop_constraint(
        "bandwidth_ledger_reporting_node_id_fkey",
        "bandwidth_ledger",
        type_="foreignkey",
    )
    op.drop_constraint(
        "user_accounts_user_id_fkey", "user_accounts", type_="foreignkey"
    )

    # Add composite unique constraint on (node_id, stream_id)
    op.create_unique_constraint(
        "uq_node_stream", "nodes", ["node_id", "stream_id"]
    )

    # Re-create a non-unique index on node_id for query performance
    op.create_index("ix_nodes_node_id", "nodes", ["node_id"])

    # Re-create probe_results and bandwidth_ledger FKs as simple column
    # references (no FK constraint since node_id is no longer unique by
    # itself — these are logical references, not enforced FKs).
    # The columns remain for querying but the FK enforcement is removed
    # because node_id alone is no longer a unique key.

    # ---------------------------------------------------------------
    # Step 5: Re-link user_accounts.user_id FK to user_identities
    # ---------------------------------------------------------------
    # We need to update user_accounts.user_id values from old node_id
    # to the new user_identity user_id.
    for old_node_id, new_user_id in node_to_identity.items():
        conn.execute(
            sa.text(
                "UPDATE user_accounts SET user_id = :uid WHERE user_id = :old"
            ),
            {"uid": new_user_id, "old": old_node_id},
        )

    # Add FK from user_accounts.user_id → user_identities.user_id
    op.create_foreign_key(
        "fk_user_accounts_user_id",
        "user_accounts",
        "user_identities",
        ["user_id"],
        ["user_id"],
    )

    # ---------------------------------------------------------------
    # Step 6: Archive and drop deprecated streams columns
    # ---------------------------------------------------------------
    # Create backup table for rollback safety
    op.create_table(
        "_deprecated_stream_fields",
        sa.Column("stream_id", sa.String(), primary_key=True),
        sa.Column("sponsor_address", sa.String()),
        sa.Column("token_balance", sa.Float()),
        sa.Column("archived_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Copy existing values into backup
    conn.execute(
        sa.text(
            "INSERT INTO _deprecated_stream_fields (stream_id, sponsor_address, token_balance) "
            "SELECT stream_id, sponsor_address, token_balance FROM streams"
        )
    )

    # Drop the deprecated columns
    op.drop_column("streams", "sponsor_address")
    op.drop_column("streams", "token_balance")

    # ---------------------------------------------------------------
    # Step 7: Add owner_user_id FK and stream_key to streams
    # ---------------------------------------------------------------
    op.add_column(
        "streams",
        sa.Column("owner_user_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "streams",
        sa.Column("stream_key", sa.String(64), nullable=True),
    )

    # Generate stream keys for existing streams and assign a default owner
    import secrets

    existing_streams = conn.execute(
        sa.text("SELECT stream_id FROM streams")
    ).fetchall()

    # If there are existing identities, use the first one as default owner;
    # otherwise create a system identity.
    default_owner = None
    if node_to_identity:
        default_owner = next(iter(node_to_identity.values()))
    elif existing_streams:
        default_owner = str(uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO user_identities (user_id, display_name, role, created_at) "
                "VALUES (:uid, 'system', 'streamer', NOW())"
            ),
            {"uid": default_owner},
        )

    for (stream_id,) in existing_streams:
        key = secrets.token_urlsafe(32)
        conn.execute(
            sa.text(
                "UPDATE streams SET stream_key = :key, owner_user_id = :owner "
                "WHERE stream_id = :sid"
            ),
            {"key": key, "owner": default_owner, "sid": stream_id},
        )

    # Make columns NOT NULL now that they're populated
    if existing_streams:
        op.alter_column("streams", "owner_user_id", nullable=False)
        op.alter_column("streams", "stream_key", nullable=False)
    else:
        # No existing data — safe to set NOT NULL directly
        op.alter_column("streams", "owner_user_id", nullable=False)
        op.alter_column("streams", "stream_key", nullable=False)

    op.create_foreign_key(
        "fk_streams_owner_user_id",
        "streams",
        "user_identities",
        ["owner_user_id"],
        ["user_id"],
    )
    op.create_index("ix_streams_stream_key", "streams", ["stream_key"])


def downgrade() -> None:
    # ---------------------------------------------------------------
    # Reverse Step 7: Remove owner_user_id and stream_key from streams
    # ---------------------------------------------------------------
    op.drop_index("ix_streams_stream_key", table_name="streams")
    op.drop_constraint("fk_streams_owner_user_id", "streams", type_="foreignkey")
    op.drop_column("streams", "stream_key")
    op.drop_column("streams", "owner_user_id")

    # ---------------------------------------------------------------
    # Reverse Step 6: Restore sponsor_address and token_balance
    # ---------------------------------------------------------------
    op.add_column(
        "streams",
        sa.Column("sponsor_address", sa.String(), nullable=True),
    )
    op.add_column(
        "streams",
        sa.Column("token_balance", sa.Float(), server_default="0.0"),
    )

    # Restore from backup
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE streams SET sponsor_address = d.sponsor_address, "
            "token_balance = d.token_balance "
            "FROM _deprecated_stream_fields d "
            "WHERE streams.stream_id = d.stream_id"
        )
    )

    # Make sponsor_address NOT NULL again (original schema)
    op.alter_column("streams", "sponsor_address", nullable=False)

    op.drop_table("_deprecated_stream_fields")

    # ---------------------------------------------------------------
    # Reverse Step 5: Re-link user_accounts back to nodes.node_id
    # ---------------------------------------------------------------
    op.drop_constraint(
        "fk_user_accounts_user_id", "user_accounts", type_="foreignkey"
    )

    # We can't perfectly reverse the UUID mapping, so we restore the
    # user_accounts.user_id to the node_id via the nodes table.
    conn.execute(
        sa.text(
            "UPDATE user_accounts ua SET user_id = n.node_id "
            "FROM nodes n "
            "WHERE n.user_id = ua.user_id"
        )
    )

    # ---------------------------------------------------------------
    # Reverse Step 4: Restore unique constraint on nodes.node_id
    # ---------------------------------------------------------------
    op.drop_index("ix_nodes_node_id", table_name="nodes")
    op.drop_constraint("uq_node_stream", "nodes", type_="unique")

    # Restore unique index on node_id
    op.create_index("ix_nodes_node_id", "nodes", ["node_id"], unique=True)

    # Restore FKs referencing nodes.node_id
    op.create_foreign_key(
        "user_accounts_user_id_fkey",
        "user_accounts",
        "nodes",
        ["user_id"],
        ["node_id"],
    )
    op.create_foreign_key(
        "bandwidth_ledger_reporting_node_id_fkey",
        "bandwidth_ledger",
        "nodes",
        ["reporting_node_id"],
        ["node_id"],
    )
    op.create_foreign_key(
        "probe_results_node_id_fkey",
        "probe_results",
        "nodes",
        ["node_id"],
        ["node_id"],
    )

    # ---------------------------------------------------------------
    # Reverse Step 3: Remove user_id from nodes
    # ---------------------------------------------------------------
    op.drop_constraint("fk_nodes_user_id", "nodes", type_="foreignkey")
    op.drop_column("nodes", "user_id")

    # ---------------------------------------------------------------
    # Reverse Steps 2 & 1: Drop user_identities
    # ---------------------------------------------------------------
    op.drop_index("ix_user_identities_email", table_name="user_identities")
    op.drop_table("user_identities")
