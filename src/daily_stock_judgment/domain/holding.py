from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker, parse_ticker


@dataclass(frozen=True, order=True)
class Holding:
    """保有 — ticker, quantity, and optional purchase record."""

    ticker: Ticker
    quantity: int
    purchase_date: date | None = None
    unit_cost: float | None = None


def parse_holding(
    raw_ticker: str,
    quantity: int,
    *,
    purchase_date: date | None = None,
    unit_cost: float | None = None,
) -> Result[Holding, str]:
    parsed = parse_ticker(raw_ticker)
    if isinstance(parsed, Err):
        return parsed
    if quantity <= 0:
        return Err("quantity must be positive")
    if unit_cost is not None and unit_cost <= 0:
        return Err("unit cost must be positive")
    return Ok(
        Holding(
            ticker=parsed.value,
            quantity=quantity,
            purchase_date=purchase_date,
            unit_cost=unit_cost,
        )
    )
