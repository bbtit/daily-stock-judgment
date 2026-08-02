from __future__ import annotations

from datetime import date
from pathlib import Path

from daily_stock_judgment.application import manage_instruments as uc
from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.sqlite_instrument_store import (
    SqliteInstrumentStore,
)
from daily_stock_judgment.infrastructure.sqlite_migrate import upgrade_to_head


def test_ストアを開き直したときウォッチリストと保有が残っている(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "app.db"
    upgrade_to_head(db_path)
    first = SqliteInstrumentStore(db_path)
    uc.add_to_watchlist(first, "7203.T")
    uc.register_holding(
        first,
        "6758.T",
        quantity=5,
        purchase_date=date(2026, 7, 31),
        unit_cost=2500.0,
    )

    second = SqliteInstrumentStore(db_path)

    assert uc.list_watchlist(second) == (Ticker("7203.T"),)
    assert uc.list_holdings(second) == (
        Holding(
            ticker=Ticker("6758.T"),
            quantity=5,
            purchase_date=date(2026, 7, 31),
            unit_cost=2500.0,
        ),
    )


def test_ストアを開き直したとき取得日と単価も残っている(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "app.db"
    upgrade_to_head(db_path)
    first = SqliteInstrumentStore(db_path)
    uc.register_holding(
        first,
        "7203.T",
        quantity=100,
        purchase_date=date(2026, 7, 31),
        unit_cost=2500.5,
    )

    second = SqliteInstrumentStore(db_path)

    assert uc.list_holdings(second) == (
        Holding(
            ticker=Ticker("7203.T"),
            quantity=100,
            purchase_date=date(2026, 7, 31),
            unit_cost=2500.5,
        ),
    )
