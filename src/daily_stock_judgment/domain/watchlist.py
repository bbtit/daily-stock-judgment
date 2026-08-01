from __future__ import annotations

from daily_stock_judgment.domain.ticker import Ticker


def replace_ticker(
    watchlist: frozenset[Ticker],
    old: Ticker,
    new: Ticker,
) -> frozenset[Ticker]:
    """Return a new watchlist with old replaced by new (pure)."""
    without_old = watchlist - {old}
    return without_old | {new}
