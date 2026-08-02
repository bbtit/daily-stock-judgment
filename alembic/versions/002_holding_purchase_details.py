"""Add purchase_date and unit_cost to holdings.

Revision ID: 002_holding_purchase_details
Revises: 001_baseline
Create Date: 2026-08-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_holding_purchase_details"
down_revision: Union[str, Sequence[str], None] = "001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "holdings", sa.Column("purchase_date", sa.Text(), nullable=True)
    )
    op.add_column(
        "holdings", sa.Column("unit_cost", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    with op.batch_alter_table("holdings") as batch:
        batch.drop_column("unit_cost")
        batch.drop_column("purchase_date")
