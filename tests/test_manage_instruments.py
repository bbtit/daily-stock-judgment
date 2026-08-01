from __future__ import annotations

from daily_stock_judgment.application import manage_instruments as uc
from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.result import Err, Ok
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.memory_instrument_store import (
    InMemoryInstrumentStore,
)


def test_ウォッチリストに追加したとき一覧にそのティッカーが含まれる() -> None:
    book = InMemoryInstrumentStore()

    result = uc.add_to_watchlist(book, "7203.T")

    assert isinstance(result, Ok)
    assert uc.list_watchlist(book) == (Ticker("7203.T"),)


def test_ウォッチリストから削除したとき一覧からそのティッカーが消える() -> None:
    book = InMemoryInstrumentStore()
    uc.add_to_watchlist(book, "7203.T")
    uc.add_to_watchlist(book, "6758.T")

    result = uc.remove_from_watchlist(book, "7203.T")

    assert isinstance(result, Ok)
    assert uc.list_watchlist(book) == (Ticker("6758.T"),)


def test_ウォッチリストのティッカーを変更したとき新しい値に置き換わる() -> None:
    book = InMemoryInstrumentStore()
    uc.add_to_watchlist(book, "7203.T")

    result = uc.replace_watchlist_ticker(book, "7203.T", "6758.T")

    assert isinstance(result, Ok)
    assert uc.list_watchlist(book) == (Ticker("6758.T"),)


def test_日本株以外のティッカーを追加しようとしたときエラーになる() -> None:
    book = InMemoryInstrumentStore()

    result = uc.add_to_watchlist(book, "AAPL")

    assert isinstance(result, Err)
    assert "7203.T" in result.error


def test_保有を数量ありとなしで登録したとき両方とも一覧に並ぶ() -> None:
    book = InMemoryInstrumentStore()

    uc.register_holding(book, "7203.T", quantity=100)
    uc.register_holding(book, "6758.T")

    assert uc.list_holdings(book) == (
        Holding(ticker=Ticker("6758.T"), quantity=None),
        Holding(ticker=Ticker("7203.T"), quantity=100.0),
    )


def test_保有を解除したとき一覧が空になる() -> None:
    book = InMemoryInstrumentStore()
    uc.register_holding(book, "7203.T", quantity=10)

    result = uc.unregister_holding(book, "7203.T")

    assert isinstance(result, Ok)
    assert uc.list_holdings(book) == ()


def test_同じ銘柄の保有を再登録したとき数量が上書きされる() -> None:
    book = InMemoryInstrumentStore()
    uc.register_holding(book, "7203.T", quantity=10)

    uc.register_holding(book, "7203.T", quantity=20)

    assert uc.list_holdings(book) == (
        Holding(ticker=Ticker("7203.T"), quantity=20.0),
    )
