from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from daily_stock_judgment.application.judgment_targets import targets_from_book
from daily_stock_judgment.application.ports import (
    InstrumentBook,
    JudgmentBook,
    JudgmentModel,
    MarketDataSource,
    SessionStatus,
)
from daily_stock_judgment.application.run_daily_judgment import (
    DailyRunResult,
    run_daily_judgments,
)
from daily_stock_judgment.domain.judgment import (
    FailedJudgment,
    JudgmentOutcome,
    SuccessfulJudgment,
)


class DayRunStore(Protocol):
    """Last full daily run snapshot (successes and failures) per as_of."""

    def save(self, as_of: date, result: DailyRunResult) -> None: ...

    def load(self, as_of: date) -> DailyRunResult | None: ...



@dataclass(frozen=True)
class JudgmentRowView:
    ticker: str
    ok: bool
    score: int | None
    label: str | None
    reason: str | None
    failure_kind: str | None

    @property
    def aria_label(self) -> str:
        if self.ok:
            return f"{self.ticker} {self.label} スコア{self.score}"
        return f"{self.ticker} {self.failure_kind}"


@dataclass(frozen=True)
class TodayJudgmentView:
    as_of: date
    market_closed: bool
    rows: tuple[JudgmentRowView, ...]


def rows_from_outcomes(
    outcomes: tuple[JudgmentOutcome, ...],
) -> tuple[JudgmentRowView, ...]:
    rows: list[JudgmentRowView] = []
    for outcome in outcomes:
        if isinstance(outcome, SuccessfulJudgment):
            rows.append(
                JudgmentRowView(
                    ticker=outcome.ticker.value,
                    ok=True,
                    score=outcome.score,
                    label=outcome.label.value,
                    reason=outcome.reason,
                    failure_kind=None,
                )
            )
        elif isinstance(outcome, FailedJudgment):
            rows.append(
                JudgmentRowView(
                    ticker=outcome.ticker.value,
                    ok=False,
                    score=None,
                    label=None,
                    reason=None,
                    failure_kind=outcome.kind.value,
                )
            )
    return tuple(rows)


def load_today_view(
    *,
    as_of: date,
    judgments: JudgmentBook,
    runs: DayRunStore,
    market: MarketDataSource,
) -> TodayJudgmentView:
    saved = runs.load(as_of)
    if saved is not None:
        return TodayJudgmentView(
            as_of=as_of,
            market_closed=saved.market_closed,
            rows=rows_from_outcomes(saved.outcomes),
        )
    if market.session_status(as_of) is SessionStatus.CLOSED:
        return TodayJudgmentView(as_of=as_of, market_closed=True, rows=())
    successes = judgments.list_for(as_of)
    return TodayJudgmentView(
        as_of=as_of,
        market_closed=False,
        rows=rows_from_outcomes(successes),
    )


def run_today_judgments(
    *,
    as_of: date,
    book: InstrumentBook,
    judgments: JudgmentBook,
    runs: DayRunStore,
    market: MarketDataSource,
    model: JudgmentModel,
) -> TodayJudgmentView:
    result = run_daily_judgments(
        as_of=as_of,
        targets=targets_from_book(book),
        market=market,
        model=model,
        store=judgments,
    )
    runs.save(as_of, result)
    return load_today_view(
        as_of=as_of, judgments=judgments, runs=runs, market=market
    )


def today_clock_tokyo(
    *,
    override: str | None = None,
) -> Callable[[], date]:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if override:
        fixed = date.fromisoformat(override)
        return lambda: fixed
    tokyo = ZoneInfo("Asia/Tokyo")
    return lambda: datetime.now(tokyo).date()
