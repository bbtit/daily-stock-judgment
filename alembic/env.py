from __future__ import annotations

import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from daily_stock_judgment.infrastructure.schema import metadata
from daily_stock_judgment.infrastructure.sqlite_migrate import sqlite_url_for

config = context.config

# Do not call fileConfig here: in-process ``upgrade_to_head`` would clobber
# the app's structlog configuration. Alembic CLI still logs via its defaults.

target_metadata = metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "app.db"


def _database_url() -> str:
    configured = config.get_main_option("sqlalchemy.url")
    if configured and configured.strip() and configured.strip() != "driver://user:pass@localhost/dbname":
        return configured
    raw = os.environ.get("DSJ_DB_PATH")
    db_path = Path(raw) if raw else DEFAULT_DB_PATH
    return sqlite_url_for(db_path)


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
