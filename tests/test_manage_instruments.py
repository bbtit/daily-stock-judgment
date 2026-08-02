from __future__ import annotations

from datetime import date

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


def test_保有を登録したとき一覧にティッカーと数量が並ぶ() -> None:
    book = InMemoryInstrumentStore()

    uc.register_holding(book, "7203.T", quantity=100)
    uc.register_holding(book, "6758.T", quantity=200)

    assert uc.list_holdings(book) == (
        Holding(ticker=Ticker("6758.T"), quantity=200),
        Holding(ticker=Ticker("7203.T"), quantity=100),
    )


def test_数量が0以下で保有を登録しようとしたときエラーになる() -> None:
    book = InMemoryInstrumentStore()

    for qty in (0, -1):
        result = uc.register_holding(book, "7203.T", quantity=qty)
        assert isinstance(result, Err)
        assert "quantity" in result.error

    assert uc.list_holdings(book) == ()


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
        Holding(ticker=Ticker("7203.T"), quantity=20),
    )


def test_保有を取得日と単価付きで登録したとき一覧にそれらが残る() -> None:
    book = InMemoryInstrumentStore()

    result = uc.register_holding(
        book,
        "7203.T",
        quantity=100,
        purchase_date=date(2026, 7, 31),
        unit_cost=2500.5,
    )

    assert isinstance(result, Ok)
    assert uc.list_holdings(book) == (
        Holding(
            ticker=Ticker("7203.T"),
            quantity=100,
            purchase_date=date(2026, 7, 31),
            unit_cost=2500.5,
        ),
    )


def test_単価が0以下で保有を登録しようとしたときエラーになる() -> None:
    book = InMemoryInstrumentStore()

    for cost in (0.0, -1.0):
        result = uc.register_holding(
            book, "7203.T", quantity=100, unit_cost=cost
        )
        assert isinstance(result, Err)
        assert "unit cost" in result.error

    assert uc.list_holdings(book) == ()
