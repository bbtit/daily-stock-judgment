"""過去日の成功判断一覧のアプリケーション seam。"""

from __future__ import annotations

from datetime import date

from daily_stock_judgment.application.past_judgments import load_past_view
from daily_stock_judgment.domain.judgment import Label, SuccessfulJudgment
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.memory_judgment_store import (
    InMemoryJudgmentStore,
)

TODAY = date(2026, 7, 31)
PAST = date(2026, 7, 30)


def _success(
    ticker: str,
    as_of: date,
    *,
    score: int = 62,
    label: Label = Label.BUY,
    reason: str = "終値3200円付近で前日比高寄り。",
) -> SuccessfulJudgment:
    return SuccessfulJudgment(
        ticker=Ticker(ticker),
        as_of=as_of,
        score=score,
        label=label,
        reason=reason,
    )


def test_過去日を選んだとき成功判断だけがスコアラベル理由付きで並ぶ() -> None:
    store = InMemoryJudgmentStore()
    store.upsert(_success("7203.T", PAST, score=62, label=Label.BUY))
    store.upsert(
        _success(
            "6758.T",
            PAST,
            score=-10,
            label=Label.WAIT,
            reason="終値は前日比ほぼ横ばい。",
        )
    )
    store.upsert(_success("9984.T", TODAY))

    view = load_past_view(today=TODAY, selected=PAST, judgments=store)

    assert view.selected == PAST
    assert view.available_dates == (PAST,)
    assert [row.ticker for row in view.rows] == ["6758.T", "7203.T"]
    assert all(row.ok for row in view.rows)
    assert view.rows[0].score == -10
    assert view.rows[0].label == "様子見"
    assert view.rows[0].reason == "終値は前日比ほぼ横ばい。"
    assert view.rows[1].score == 62
    assert view.rows[1].label == "買う"
