from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


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
        "run start as_of=%s targets=%d [%s]",
        as_of.isoformat(),
        len(targets),
        tickers,
    )
    status = market.session_status(as_of)
    if status is SessionStatus.CLOSED:
        logger.info("run skip market_closed as_of=%s", as_of.isoformat())
        return DailyRunResult(market_closed=True, outcomes=())
    logger.info("session open as_of=%s", as_of.isoformat())

    outcomes: list[JudgmentOutcome] = []
    for target in targets:
        outcome = _judge_one(as_of, target, market, model)
        outcomes.append(outcome)
        if isinstance(outcome, SuccessfulJudgment):
            store.upsert(outcome)
            logger.info(
                "outcome ok ticker=%s score=%s label=%s reason=%s",
                outcome.ticker.value,
                outcome.score,
                outcome.label.value,
                _clip(outcome.reason, 120),
            )
        else:
            logger.warning(
                "outcome fail ticker=%s kind=%s",
                outcome.ticker.value,
                outcome.kind.value,
            )
    ok = sum(1 for o in outcomes if isinstance(o, SuccessfulJudgment))
    failed = len(outcomes) - ok
    logger.info(
        "run done as_of=%s ok=%d failed=%d",
        as_of.isoformat(),
        ok,
        failed,
    )
    return DailyRunResult(market_closed=False, outcomes=tuple(outcomes))


def _judge_one(
    as_of: date,
    target: JudgmentTarget,
    market: MarketDataSource,
    model: JudgmentModel,
) -> JudgmentOutcome:
    holding = "holding" if target.is_holding else "watch"
    logger.info("judge start ticker=%s role=%s", target.ticker.value, holding)
    bars_result = _fetch_bars(market, target.ticker, as_of)
    if isinstance(bars_result, Err):
        logger.warning(
            "bars fail ticker=%s kind=%s",
            target.ticker.value,
            bars_result.error.value,
        )
        return FailedJudgment(
            ticker=target.ticker, as_of=as_of, kind=bars_result.error
        )
    bars = bars_result.value
    logger.info(
        "bars ok ticker=%s count=%d last=%s",
        target.ticker.value,
        len(bars),
        bars[-1].date.isoformat() if bars else "-",
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
                "bars retry ticker=%s attempt=%d kind=%s",
                ticker.value,
                attempt + 1,
                result.error.value,
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
                    "model exhausted ticker=%s call_failures=%d",
                    target.ticker.value,
                    call_failures + 1,
                )
                return Err(FailureKind.JUDGMENT_FAILED)
            call_failures += 1
            logger.info(
                "model retry ticker=%s call_failures=%d",
                target.ticker.value,
                call_failures,
            )
            continue

        checked = validate_draft(raw.value)
        if isinstance(checked, Ok):
            return checked
        if validation_failures >= _DRAFT_REGENERATE:
            logger.warning(
                "draft validation exhausted ticker=%s score=%s reason=%s",
                target.ticker.value,
                raw.value.score,
                _clip(raw.value.reason, 120),
            )
            return Err(FailureKind.JUDGMENT_FAILED)
        validation_failures += 1
        logger.info(
            "draft regenerate ticker=%s validation_failures=%d",
            target.ticker.value,
            validation_failures,
        )


def _clip(text: str, limit: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
