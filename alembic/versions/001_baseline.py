"""Baseline schema: watchlist, holdings, judgments, day_runs.

Revision ID: 001_baseline
Revises:
Create Date: 2026-08-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("ticker", sa.Text(collation="NOCASE"), primary_key=True),
    )
    op.create_table(
        "holdings",
        sa.Column("ticker", sa.Text(collation="NOCASE"), primary_key=True),
        sa.Column("quantity", sa.Float(), nullable=True),
    )
    op.create_table(
        "judgments",
        sa.Column("ticker", sa.Text(collation="NOCASE"), nullable=False),
        sa.Column("as_of", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("ticker", "as_of"),
    )
    op.create_table(
        "day_runs",
        sa.Column("as_of", sa.Text(), primary_key=True),
        sa.Column("market_closed", sa.Integer(), nullable=False),
        sa.Column("outcomes_json", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("day_runs")
    op.drop_table("judgments")
    op.drop_table("holdings")
    op.drop_table("watchlist")
