from __future__ import annotations

from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.domain.watchlist import replace_ticker


def test_replace_ticker_is_pure() -> None:
    original = frozenset({Ticker("7203.T"), Ticker("6758.T")})

    updated = replace_ticker(original, Ticker("7203.T"), Ticker("9984.T"))

    assert original == frozenset({Ticker("7203.T"), Ticker("6758.T")})
    assert updated == frozenset({Ticker("6758.T"), Ticker("9984.T")})
