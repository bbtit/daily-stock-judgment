from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Union

from daily_stock_judgment.domain.ticker import Ticker


class Label(str, Enum):
    BUY = "買う"
    SELL = "売る"
    WAIT = "様子見"


class FailureKind(str, Enum):
    DATA_MISSING = "データ未着"
    UNAVAILABLE = "取得不可"
    JUDGMENT_FAILED = "判断失敗"


@dataclass(frozen=True)
class JudgmentDraft:
    """LLM output before system labeling."""

    score: int
    reason: str


@dataclass(frozen=True)
class SuccessfulJudgment:
    ticker: Ticker
    as_of: date
    score: int
    label: Label
    reason: str


@dataclass(frozen=True)
class FailedJudgment:
    ticker: Ticker
    as_of: date
    kind: FailureKind


JudgmentOutcome = Union[SuccessfulJudgment, FailedJudgment]


@dataclass(frozen=True)
class JudgmentTarget:
    ticker: Ticker
    is_holding: bool
