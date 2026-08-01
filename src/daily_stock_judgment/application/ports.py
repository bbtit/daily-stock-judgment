from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Protocol

from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.judgment import (
    FailureKind,
    JudgmentDraft,
    SuccessfulJudgment,
)
from daily_stock_judgment.domain.result import Result
from daily_stock_judgment.domain.ticker import Ticker


class SessionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class InstrumentBook(Protocol):
    """Persistence port for watchlist and holdings."""

    def list_watchlist(self) -> tuple[Ticker, ...]: ...

    def add_to_watchlist(self, ticker: Ticker) -> None: ...

    def remove_from_watchlist(self, ticker: Ticker) -> None: ...

    def replace_watchlist_ticker(self, old: Ticker, new: Ticker) -> None: ...

    def list_holdings(self) -> tuple[Holding, ...]: ...

    def upsert_holding(self, holding: Holding) -> None: ...

    def remove_holding(self, ticker: Ticker) -> None: ...


class MarketDataSource(Protocol):
    """Daily bars and session status for a judgment day."""

    def session_status(self, as_of: date) -> SessionStatus: ...

    def bars_for(
        self, ticker: Ticker, as_of: date
    ) -> Result[tuple[Bar, ...], FailureKind]: ...


class JudgmentModel(Protocol):
    """Produces score + reason for one ticker (no label)."""

    def draft(
        self,
        ticker: Ticker,
        as_of: date,
        is_holding: bool,
        bars: tuple[Bar, ...],
    ) -> Result[JudgmentDraft, FailureKind]: ...


class JudgmentBook(Protocol):
    """Persistence for successful judgments only."""

    def upsert(self, judgment: SuccessfulJudgment) -> None: ...

    def list_for(self, as_of: date) -> tuple[SuccessfulJudgment, ...]: ...

    def list_as_of_dates(self) -> tuple[date, ...]: ...
