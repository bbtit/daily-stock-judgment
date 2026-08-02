from __future__ import annotations

import sqlite3
from pathlib import Path

from daily_stock_judgment.application import manage_instruments as uc
from daily_stock_judgment.composition import create_app
from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.sqlite_instrument_store import (
    SqliteInstrumentStore,
)


def test_空のDBでcreate_appするとマイグレーション後にストアが使える(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "app.db"

    create_app(db_path)

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "watchlist",
        "holdings",
        "judgments",
        "day_runs",
    } <= tables

    store = SqliteInstrumentStore(db_path)
    uc.add_to_watchlist(store, "7203.T")
    uc.register_holding(store, "6758.T", quantity=3)
    assert uc.list_watchlist(store) == (Ticker("7203.T"),)
    assert uc.list_holdings(store) == (
        Holding(ticker=Ticker("6758.T"), quantity=3),
    )

    from datetime import date

    from daily_stock_judgment.domain.judgment import Label, SuccessfulJudgment
    from daily_stock_judgment.infrastructure.sqlite_judgment_store import (
        SqliteJudgmentStore,
    )

    as_of = date(2026, 7, 31)
    judgments = SqliteJudgmentStore(db_path)
    judgments.upsert(
        SuccessfulJudgment(
            ticker=Ticker("7203.T"),
            as_of=as_of,
            score=10,
            label=Label.WAIT,
            reason="終値100円前後。",
        )
    )
    assert len(judgments.list_for(as_of)) == 1
