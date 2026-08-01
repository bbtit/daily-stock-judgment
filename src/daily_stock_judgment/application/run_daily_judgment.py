from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from daily_stock_judgment.application.ports import (
    JudgmentBook,
    JudgmentModel,
    MarketDataSource,
    SessionStatus,
)
from daily_stock_judgment.application.validate_draft import validate_draft
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import (
    FailedJudgment,
    FailureKind,
    JudgmentDraft,
    JudgmentOutcome,
    JudgmentTarget,
    SuccessfulJudgment,
)
from daily_stock_judgment.domain.labeling import label_for
from daily_stock_judgment.domain.result import Err, Ok, Result


@dataclass(frozen=True)
class DailyRunResult:
    market_closed: bool
    outcomes: tuple[JudgmentOutcome, ...]


_MARKET_FETCH_RETRIES = 2
_MODEL_CALL_RETRIES = 1
_DRAFT_REGENERATE = 1


def run_daily_judgments(
    *,
    as_of: date,
    targets: tuple[JudgmentTarget, ...],
    market: MarketDataSource,
    model: JudgmentModel,
    store: JudgmentBook,
) -> DailyRunResult:
    if market.session_status(as_of) is SessionStatus.CLOSED:
        return DailyRunResult(market_closed=True, outcomes=())

    outcomes: list[JudgmentOutcome] = []
    for target in targets:
        outcome = _judge_one(as_of, target, market, model)
        outcomes.append(outcome)
        if isinstance(outcome, SuccessfulJudgment):
            store.upsert(outcome)
    return DailyRunResult(market_closed=False, outcomes=tuple(outcomes))


def _judge_one(
    as_of: date,
    target: JudgmentTarget,
    market: MarketDataSource,
    model: JudgmentModel,
) -> JudgmentOutcome:
    bars_result = _fetch_bars(market, target.ticker, as_of)
    if isinstance(bars_result, Err):
        return FailedJudgment(
            ticker=target.ticker, as_of=as_of, kind=bars_result.error
        )

    draft_result = _draft_with_retries(
        model, target, as_of, bars_result.value
    )
    if isinstance(draft_result, Err):
        return FailedJudgment(
            ticker=target.ticker, as_of=as_of, kind=FailureKind.JUDGMENT_FAILED
        )

    draft = draft_result.value
    return SuccessfulJudgment(
        ticker=target.ticker,
        as_of=as_of,
        score=draft.score,
        label=label_for(draft.score, is_holding=target.is_holding),
        reason=draft.reason,
    )


def _fetch_bars(
    market: MarketDataSource,
    ticker,
    as_of: date,
) -> Result[tuple[Bar, ...], FailureKind]:
    last: Err[FailureKind] | None = None
    for attempt in range(1 + _MARKET_FETCH_RETRIES):
        result = market.bars_for(ticker, as_of)
        if isinstance(result, Ok):
            return Ok(result.value[-60:])
        last = result
        if result.error is not FailureKind.DATA_MISSING:
            return result
        if attempt == _MARKET_FETCH_RETRIES:
            break
    assert last is not None
    return last


def _draft_with_retries(
    model: JudgmentModel,
    target: JudgmentTarget,
    as_of: date,
    bars: tuple[Bar, ...],
) -> Result[JudgmentDraft, FailureKind]:
    call_failures = 0
    validation_failures = 0

    while True:
        raw = model.draft(target.ticker, as_of, target.is_holding, bars)
        if isinstance(raw, Err):
            if call_failures >= _MODEL_CALL_RETRIES:
                return Err(FailureKind.JUDGMENT_FAILED)
            call_failures += 1
            continue

        checked = validate_draft(raw.value)
        if isinstance(checked, Ok):
            return checked
        if validation_failures >= _DRAFT_REGENERATE:
            return Err(FailureKind.JUDGMENT_FAILED)
        validation_failures += 1
