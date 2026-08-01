from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from daily_stock_judgment.application.ports import JudgmentBook
from daily_stock_judgment.application.today_judgments import (
    JudgmentRowView,
    rows_from_outcomes,
)


@dataclass(frozen=True)
class PastJudgmentView:
    selected: date | None
    available_dates: tuple[date, ...]
    rows: tuple[JudgmentRowView, ...]


def load_past_view(
    *,
    today: date,
    selected: date | None,
    judgments: JudgmentBook,
) -> PastJudgmentView:
    available = tuple(d for d in judgments.list_as_of_dates() if d < today)
    if selected is None or selected not in available:
        return PastJudgmentView(
            selected=None,
            available_dates=available,
            rows=(),
        )
    return PastJudgmentView(
        selected=selected,
        available_dates=available,
        rows=rows_from_outcomes(judgments.list_for(selected)),
    )
