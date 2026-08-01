"""Temporary market/LLM stand-ins until tickets 17 and 18 land.

Deterministic bars and drafts so localhost UI can exercise the runner.
"""

from __future__ import annotations

from datetime import date, timedelta

from daily_stock_judgment.application.ports import SessionStatus
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind, JudgmentDraft
from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker


class DemoMarketData:
    """Always-open session; synthetic bars ending on as_of."""

    def session_status(self, as_of: date) -> SessionStatus:
        del as_of
        return SessionStatus.OPEN

    def bars_for(
        self, ticker: Ticker, as_of: date
    ) -> Result[tuple[Bar, ...], FailureKind]:
        del ticker
        bars = []
        for offset in range(4, -1, -1):
            day = as_of - timedelta(days=offset)
            close = 1000.0 + offset
            bars.append(
                Bar(
                    date=day,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=10_000.0,
                )
            )
        return Ok(tuple(bars))


class DemoJudgmentModel:
    """Fixed bullish draft that passes reason validation."""

    def draft(
        self,
        ticker: Ticker,
        as_of: date,
        is_holding: bool,
        bars: tuple[Bar, ...],
    ) -> Result[JudgmentDraft, FailureKind]:
        del as_of, is_holding, bars
        return Ok(
            JudgmentDraft(
                score=62,
                reason=f"{ticker.value}の終値は前日比で高寄り。",
            )
        )
