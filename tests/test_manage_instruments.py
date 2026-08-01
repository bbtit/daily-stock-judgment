from __future__ import annotations

from daily_stock_judgment.application import manage_instruments as uc
from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.result import Err, Ok
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.memory_instrument_store import (
    InMemoryInstrumentStore,
)


def test_add_and_list_watchlist() -> None:
    book = InMemoryInstrumentStore()

    result = uc.add_to_watchlist(book, "7203.T")

    assert isinstance(result, Ok)
    assert uc.list_watchlist(book) == (Ticker("7203.T"),)


def test_remove_from_watchlist() -> None:
    book = InMemoryInstrumentStore()
    uc.add_to_watchlist(book, "7203.T")
    uc.add_to_watchlist(book, "6758.T")

    result = uc.remove_from_watchlist(book, "7203.T")

    assert isinstance(result, Ok)
    assert uc.list_watchlist(book) == (Ticker("6758.T"),)


def test_register_holding_with_optional_quantity() -> None:
    book = InMemoryInstrumentStore()

    uc.register_holding(book, "7203.T", quantity=100)
    uc.register_holding(book, "6758.T")

    assert uc.list_holdings(book) == (
        Holding(ticker=Ticker("6758.T"), quantity=None),
        Holding(ticker=Ticker("7203.T"), quantity=100.0),
    )


def test_unregister_holding() -> None:
    book = InMemoryInstrumentStore()
    uc.register_holding(book, "7203.T", quantity=10)

    result = uc.unregister_holding(book, "7203.T")

    assert isinstance(result, Ok)
    assert uc.list_holdings(book) == ()


def test_update_holding_quantity() -> None:
    book = InMemoryInstrumentStore()
    uc.register_holding(book, "7203.T", quantity=10)

    uc.register_holding(book, "7203.T", quantity=20)

    assert uc.list_holdings(book) == (
        Holding(ticker=Ticker("7203.T"), quantity=20.0),
    )


def test_replace_watchlist_ticker() -> None:
    book = InMemoryInstrumentStore()
    uc.add_to_watchlist(book, "7203.T")

    result = uc.replace_watchlist_ticker(book, "7203.T", "6758.T")

    assert isinstance(result, Ok)
    assert uc.list_watchlist(book) == (Ticker("6758.T"),)


def test_rejects_non_japan_yahoo_ticker() -> None:
    book = InMemoryInstrumentStore()

    result = uc.add_to_watchlist(book, "AAPL")

    assert isinstance(result, Err)
    assert "7203.T" in result.error
