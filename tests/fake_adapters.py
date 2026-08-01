"""Test doubles for judgment-runner ports (not production adapters)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from daily_stock_judgment.application.ports import SessionStatus
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind, JudgmentDraft
from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker


@dataclass
class FakeMarketData:
    """Configurable market port for seam tests."""

    closed_days: set[date] = field(default_factory=set)
    bars_by_ticker: dict[str, list[Bar]] = field(default_factory=dict)
    failure_by_ticker: dict[str, FailureKind] = field(default_factory=dict)
    fetch_calls: dict[str, int] = field(default_factory=dict)

    def session_status(self, as_of: date) -> SessionStatus:
        return (
            SessionStatus.CLOSED
            if as_of in self.closed_days
            else SessionStatus.OPEN
        )

    def bars_for(
        self, ticker: Ticker, as_of: date
    ) -> Result[tuple[Bar, ...], FailureKind]:
        del as_of
        key = ticker.value
        self.fetch_calls[key] = self.fetch_calls.get(key, 0) + 1
        if key in self.failure_by_ticker:
            return Err(self.failure_by_ticker[key])
        if key not in self.bars_by_ticker:
            return Err(FailureKind.UNAVAILABLE)
        return Ok(tuple(self.bars_by_ticker[key]))


@dataclass
class FakeJudgmentModel:
    """Configurable LLM port for seam tests."""

    drafts_by_ticker: dict[str, JudgmentDraft | list[JudgmentDraft]] = field(
        default_factory=dict
    )
    call_failures_remaining: dict[str, int] = field(default_factory=dict)
    call_counts: dict[str, int] = field(default_factory=dict)

    def draft(
        self,
        ticker: Ticker,
        as_of: date,
        is_holding: bool,
        bars: tuple[Bar, ...],
    ) -> Result[JudgmentDraft, FailureKind]:
        del as_of, is_holding, bars
        key = ticker.value
        self.call_counts[key] = self.call_counts.get(key, 0) + 1
        left = self.call_failures_remaining.get(key, 0)
        if left > 0:
            self.call_failures_remaining[key] = left - 1
            return Err(FailureKind.JUDGMENT_FAILED)

        payload = self.drafts_by_ticker.get(key)
        if payload is None:
            return Err(FailureKind.JUDGMENT_FAILED)
        if isinstance(payload, list):
            if not payload:
                return Err(FailureKind.JUDGMENT_FAILED)
            return Ok(payload.pop(0))
        return Ok(payload)
