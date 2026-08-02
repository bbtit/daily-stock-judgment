"""SQLAlchemy Core schema for Alembic (not used by sqlite3 stores)."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
)

metadata = MetaData()

watchlist = Table(
    "watchlist",
    metadata,
    Column("ticker", Text(collation="NOCASE"), primary_key=True),
)

holdings = Table(
    "holdings",
    metadata,
    Column("ticker", Text(collation="NOCASE"), primary_key=True),
    Column("quantity", Integer, nullable=False),
    Column("purchase_date", Text, nullable=True),
    Column("unit_cost", Float, nullable=True),
)

judgments = Table(
    "judgments",
    metadata,
    Column("ticker", Text(collation="NOCASE"), nullable=False),
    Column("as_of", Text, nullable=False),
    Column("score", Integer, nullable=False),
    Column("label", Text, nullable=False),
    Column("reason", Text, nullable=False),
    PrimaryKeyConstraint("ticker", "as_of"),
)

day_runs = Table(
    "day_runs",
    metadata,
    Column("as_of", Text, primary_key=True),
    Column("market_closed", Integer, nullable=False),
    Column("outcomes_json", Text, nullable=False),
)
