from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import structlog

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

logger = structlog.get_logger(__name__)


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
    tickers = ",".join(t.ticker.value for t in targets) or "(none)"
    logger.info(
        "run_start",
        as_of=as_of.isoformat(),
        targets=len(targets),
        tickers=tickers,
    )
    status = market.session_status(as_of)
    if status is SessionStatus.CLOSED:
        logger.info("run_skip_market_closed", as_of=as_of.isoformat())
        return DailyRunResult(market_closed=True, outcomes=())
    logger.info("session_open", as_of=as_of.isoformat())

    outcomes: list[JudgmentOutcome] = []
    for target in targets:
        outcome = _judge_one(as_of, target, market, model)
        outcomes.append(outcome)
        if isinstance(outcome, SuccessfulJudgment):
            store.upsert(outcome)
            logger.info(
                "outcome_ok",
                ticker=outcome.ticker.value,
                score=outcome.score,
                label=outcome.label.value,
                reason=_clip(outcome.reason, 120),
            )
        else:
            logger.warning(
                "outcome_fail",
                ticker=outcome.ticker.value,
                kind=outcome.kind.value,
            )
    ok = sum(1 for o in outcomes if isinstance(o, SuccessfulJudgment))
    failed = len(outcomes) - ok
    logger.info(
        "run_done",
        as_of=as_of.isoformat(),
        ok=ok,
        failed=failed,
    )
    return DailyRunResult(market_closed=False, outcomes=tuple(outcomes))


def _judge_one(
    as_of: date,
    target: JudgmentTarget,
    market: MarketDataSource,
    model: JudgmentModel,
) -> JudgmentOutcome:
    holding = "holding" if target.is_holding else "watch"
    logger.info(
        "judge_start",
        ticker=target.ticker.value,
        role=holding,
    )
    bars_result = _fetch_bars(market, target.ticker, as_of)
    if isinstance(bars_result, Err):
        logger.warning(
            "bars_fail",
            ticker=target.ticker.value,
            kind=bars_result.error.value,
        )
        return FailedJudgment(
            ticker=target.ticker, as_of=as_of, kind=bars_result.error
        )
    bars = bars_result.value
    logger.info(
        "bars_ok",
        ticker=target.ticker.value,
        count=len(bars),
        last=bars[-1].date.isoformat() if bars else "-",
    )

    draft_result = _draft_with_retries(model, target, as_of, bars)
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
        if result.error is FailureKind.DATA_MISSING:
            logger.info(
                "bars_retry",
                ticker=ticker.value,
                attempt=attempt + 1,
                kind=result.error.value,
            )
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
                logger.warning(
                    "model_exhausted",
                    ticker=target.ticker.value,
                    call_failures=call_failures + 1,
                )
                return Err(FailureKind.JUDGMENT_FAILED)
            call_failures += 1
            logger.info(
                "model_retry",
                ticker=target.ticker.value,
                call_failures=call_failures,
            )
            continue

        checked = validate_draft(raw.value)
        if isinstance(checked, Ok):
            return checked
        if validation_failures >= _DRAFT_REGENERATE:
            logger.warning(
                "draft_validation_exhausted",
                ticker=target.ticker.value,
                score=raw.value.score,
                reason=_clip(raw.value.reason, 120),
            )
            return Err(FailureKind.JUDGMENT_FAILED)
        validation_failures += 1
        logger.info(
            "draft_regenerate",
            ticker=target.ticker.value,
            validation_failures=validation_failures,
        )


def _clip(text: str, limit: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
