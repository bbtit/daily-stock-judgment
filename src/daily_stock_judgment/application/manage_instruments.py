from __future__ import annotations

from datetime import date

from daily_stock_judgment.application.ports import InstrumentBook
from daily_stock_judgment.domain.holding import Holding, parse_holding
from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker, parse_ticker


def list_watchlist(book: InstrumentBook) -> tuple[Ticker, ...]:
    return book.list_watchlist()


def add_to_watchlist(book: InstrumentBook, raw_ticker: str) -> Result[None, str]:
    parsed = parse_ticker(raw_ticker)
    if isinstance(parsed, Err):
        return parsed
    book.add_to_watchlist(parsed.value)
    return Ok(None)


def remove_from_watchlist(
    book: InstrumentBook, raw_ticker: str
) -> Result[None, str]:
    parsed = parse_ticker(raw_ticker)
    if isinstance(parsed, Err):
        return parsed
    book.remove_from_watchlist(parsed.value)
    return Ok(None)


def replace_watchlist_ticker(
    book: InstrumentBook, raw_old: str, raw_new: str
) -> Result[None, str]:
    old = parse_ticker(raw_old)
    if isinstance(old, Err):
        return old
    new = parse_ticker(raw_new)
    if isinstance(new, Err):
        return new
    book.replace_watchlist_ticker(old.value, new.value)
    return Ok(None)


def list_holdings(book: InstrumentBook) -> tuple[Holding, ...]:
    return book.list_holdings()


def register_holding(
    book: InstrumentBook,
    raw_ticker: str,
    quantity: int,
    *,
    purchase_date: date | None = None,
    unit_cost: float | None = None,
) -> Result[None, str]:
    parsed = parse_holding(
        raw_ticker,
        quantity,
        purchase_date=purchase_date,
        unit_cost=unit_cost,
    )
    if isinstance(parsed, Err):
        return parsed
    book.upsert_holding(parsed.value)
    return Ok(None)


def unregister_holding(
    book: InstrumentBook, raw_ticker: str
) -> Result[None, str]:
    parsed = parse_ticker(raw_ticker)
    if isinstance(parsed, Err):
        return parsed
    book.remove_holding(parsed.value)
    return Ok(None)
