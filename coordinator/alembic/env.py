"""Alembic migration environment for StreamrP2P Coordinator.

Reads DATABASE_URL from the environment (same variable used by app/database.py).
Imports models.Base so autogenerate can detect schema diffs.
"""

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Load .env so DATABASE_URL is available in local dev
load_dotenv()

# Import the declarative Base that holds all model metadata
from app.models import Base  # noqa: E402

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Set up Python logging from the ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our model metadata for autogenerate support
target_metadata = Base.metadata

# Override sqlalchemy.url with the environment variable
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://streamr:streamr@localhost:5432/streamr_poc",
)
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
