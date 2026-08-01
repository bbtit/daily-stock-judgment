from __future__ import annotations

from datetime import date
from pathlib import Path

from daily_stock_judgment.domain.judgment import Label, SuccessfulJudgment
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.sqlite_judgment_store import (
    SqliteJudgmentStore,
)

AS_OF = date(2026, 7, 31)


def test_ストアを開き直したとき成功判断が残り同日上書きも反映される(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "app.db"
    first = SqliteJudgmentStore(db_path)
    first.upsert(
        SuccessfulJudgment(
            ticker=Ticker("7203.T"),
            as_of=AS_OF,
            score=10,
            label=Label.WAIT,
            reason="終値100円前後。",
        )
    )
    first.upsert(
        SuccessfulJudgment(
            ticker=Ticker("7203.T"),
            as_of=AS_OF,
            score=70,
            label=Label.BUY,
            reason="終値は高寄り。",
        )
    )

    second = SqliteJudgmentStore(db_path)
    saved = second.list_for(AS_OF)

    assert len(saved) == 1
    assert saved[0].score == 70
    assert saved[0].label is Label.BUY
