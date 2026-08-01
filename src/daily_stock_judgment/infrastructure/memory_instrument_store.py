from __future__ import annotations

from dataclasses import dataclass, replace

from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.domain.watchlist import replace_ticker


@dataclass(frozen=True)
class _State:
    watchlist: frozenset[Ticker] = frozenset()
    holdings: frozenset[Holding] = frozenset()


class InMemoryInstrumentStore:
    """Immutable in-memory InstrumentBook for tests."""

    def __init__(self) -> None:
        self._state = _State()

    def list_watchlist(self) -> tuple[Ticker, ...]:
        return tuple(sorted(self._state.watchlist))

    def add_to_watchlist(self, ticker: Ticker) -> None:
        self._state = replace(
            self._state, watchlist=self._state.watchlist | {ticker}
        )

    def remove_from_watchlist(self, ticker: Ticker) -> None:
        self._state = replace(
            self._state, watchlist=self._state.watchlist - {ticker}
        )

    def replace_watchlist_ticker(self, old: Ticker, new: Ticker) -> None:
        self._state = replace(
            self._state,
            watchlist=replace_ticker(self._state.watchlist, old, new),
        )

    def list_holdings(self) -> tuple[Holding, ...]:
        return tuple(sorted(self._state.holdings))

    def upsert_holding(self, holding: Holding) -> None:
        without = frozenset(
            h for h in self._state.holdings if h.ticker != holding.ticker
        )
        self._state = replace(self._state, holdings=without | {holding})

    def remove_holding(self, ticker: Ticker) -> None:
        self._state = replace(
            self._state,
            holdings=frozenset(
                h for h in self._state.holdings if h.ticker != ticker
            ),
        )
