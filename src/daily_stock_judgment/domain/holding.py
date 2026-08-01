from __future__ import annotations

from dataclasses import dataclass

from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker, parse_ticker


@dataclass(frozen=True, order=True)
class Holding:
    """保有 — ticker plus optional quantity."""

    ticker: Ticker
    quantity: float | None = None


def parse_holding(
    raw_ticker: str, quantity: float | None = None
) -> Result[Holding, str]:
    parsed = parse_ticker(raw_ticker)
    if isinstance(parsed, Err):
        return parsed
    if quantity is not None and quantity < 0:
        return Err("quantity must not be negative")
    return Ok(Holding(ticker=parsed.value, quantity=quantity))
