"""
Alembic environment. Uses DATABASE_URL from the environment (set in Docker/prod)
so migrations run against the same database as the app.
"""
import os
import sys

# Add app to path so we can import database and models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy import pool

# Import app's Base so metadata is available; import models so they register with Base
from app.database import Base
import app.models  # noqa: F401 - register all models with Base.metadata

# Use DATABASE_URL from environment (Docker/prod) or fall back to sqlite for local
config = context.config
url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url", "")
if not url or url.strip() == "" or "driver://" in url:
    url = "sqlite:///./nba_props.db"
if url.startswith("postgresql://") and "psycopg2" not in url:
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        url,
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
