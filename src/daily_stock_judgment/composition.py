from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path

from fastapi import FastAPI

from daily_stock_judgment.application.ports import JudgmentModel, MarketDataSource
from daily_stock_judgment.application.today_judgments import today_clock_tokyo
from daily_stock_judgment.infrastructure.demo_adapters import (
    DemoJudgmentModel,
    DemoMarketData,
)
from daily_stock_judgment.infrastructure.sqlite_day_run_store import (
    SqliteDayRunStore,
)
from daily_stock_judgment.infrastructure.sqlite_instrument_store import (
    SqliteInstrumentStore,
)
from daily_stock_judgment.infrastructure.sqlite_judgment_store import (
    SqliteJudgmentStore,
)
from daily_stock_judgment.infrastructure.yfinance_market import YFinanceMarketData
from daily_stock_judgment.presentation.web import create_app as create_web_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DB_PATH = (
    Path.home() / ".local" / "share" / "daily-stock-judgment" / "app.db"
)
DEFAULT_DB_PATH = (
    Path(os.environ["DSJ_DB_PATH"])
    if "DSJ_DB_PATH" in os.environ
    else PROJECT_ROOT / "data" / "app.db"
)


def prepare_db_path(db_path: Path) -> Path:
    """Prefer project-local DB; migrate once from the legacy home path."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if (
        db_path == DEFAULT_DB_PATH
        and "DSJ_DB_PATH" not in os.environ
        and not db_path.exists()
        and LEGACY_DB_PATH.exists()
    ):
        shutil.move(str(LEGACY_DB_PATH), str(db_path))
    return db_path


def create_app(
    db_path: Path | None = None,
    *,
    market: MarketDataSource | None = None,
    model: JudgmentModel | None = None,
    today: Callable[[], date] | None = None,
) -> FastAPI:
    resolved = prepare_db_path(db_path or DEFAULT_DB_PATH)
    book = SqliteInstrumentStore(resolved)
    judgments = SqliteJudgmentStore(resolved)
    runs = SqliteDayRunStore(resolved)
    return create_web_app(
        book,
        judgments=judgments,
        runs=runs,
        market=market or _default_market(),
        model=model or DemoJudgmentModel(),  # real CLI in ticket 18
        today=today or today_clock_tokyo(override=os.environ.get("DSJ_AS_OF")),
    )


def _default_market() -> MarketDataSource:
    # DSJ_MARKET=demo keeps deterministic bars for local/E2E without Yahoo.
    if os.environ.get("DSJ_MARKET", "yfinance") == "demo":
        return DemoMarketData()
    return YFinanceMarketData()


app = create_app()
