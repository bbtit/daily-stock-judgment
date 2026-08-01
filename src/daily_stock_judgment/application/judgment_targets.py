from __future__ import annotations

from daily_stock_judgment.application.ports import InstrumentBook
from daily_stock_judgment.domain.judgment import JudgmentTarget


def targets_from_book(book: InstrumentBook) -> tuple[JudgmentTarget, ...]:
    """Watchlist ∪ holdings, with holding flag for label rules."""
    holding_tickers = {h.ticker for h in book.list_holdings()}
    tickers = set(book.list_watchlist()) | holding_tickers
    return tuple(
        JudgmentTarget(ticker=ticker, is_holding=ticker in holding_tickers)
        for ticker in sorted(tickers)
    )
