from __future__ import annotations

from typing import Protocol

from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.ticker import Ticker


class InstrumentBook(Protocol):
    """Persistence port for watchlist and holdings."""

    def list_watchlist(self) -> tuple[Ticker, ...]: ...

    def add_to_watchlist(self, ticker: Ticker) -> None: ...

    def remove_from_watchlist(self, ticker: Ticker) -> None: ...

    def replace_watchlist_ticker(self, old: Ticker, new: Ticker) -> None: ...

    def list_holdings(self) -> tuple[Holding, ...]: ...

    def upsert_holding(self, holding: Holding) -> None: ...

    def remove_holding(self, ticker: Ticker) -> None: ...
