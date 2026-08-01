"""過去日の判断一覧の HTTP seam。"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from daily_stock_judgment.application.run_daily_judgment import DailyRunResult
from daily_stock_judgment.domain.judgment import (
    FailedJudgment,
    FailureKind,
    Label,
    SuccessfulJudgment,
)
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.memory_day_run_store import (
    InMemoryDayRunStore,
)
from daily_stock_judgment.infrastructure.memory_instrument_store import (
    InMemoryInstrumentStore,
)
from daily_stock_judgment.infrastructure.memory_judgment_store import (
    InMemoryJudgmentStore,
)
from daily_stock_judgment.presentation.web import create_app
from tests.fake_adapters import FakeJudgmentModel, FakeMarketData

TODAY = date(2026, 7, 31)
PAST = date(2026, 7, 30)


def _client(judgments: InMemoryJudgmentStore) -> TestClient:
    app = create_app(
        InMemoryInstrumentStore(),
        judgments=judgments,
        runs=InMemoryDayRunStore(),
        market=FakeMarketData(),
        model=FakeJudgmentModel(),
        today=lambda: TODAY,
    )
    return TestClient(app)


def test_過去日を選んだとき成功判断のスコアラベル理由が一覧される() -> None:
    judgments = InMemoryJudgmentStore()
    judgments.upsert(
        SuccessfulJudgment(
            ticker=Ticker("7203.T"),
            as_of=PAST,
            score=62,
            label=Label.BUY,
            reason="終値3200円付近で前日比高寄り。",
        )
    )
    client = _client(judgments)

    response = client.get("/", params={"history_as_of": PAST.isoformat()})

    assert response.status_code == 200
    assert 'aria-label="7203.T 買う スコア62"' in response.text
    assert "終値3200円付近で前日比高寄り。" in response.text
    assert 'aria-label="過去の判断日"' in response.text
    assert f'value="{PAST.isoformat()}"' in response.text


def test_過去日一覧に今日の判断日は候補に出ない() -> None:
    judgments = InMemoryJudgmentStore()
    judgments.upsert(
        SuccessfulJudgment(
            ticker=Ticker("7203.T"),
            as_of=TODAY,
            score=62,
            label=Label.BUY,
            reason="今日の成功。",
        )
    )
    client = _client(judgments)

    response = client.get("/")

    assert response.status_code == 200
    assert "まだ過去の判断はありません。" in response.text
    assert 'name="history_as_of"' not in response.text


def test_過去日一覧に失敗区分は出ない() -> None:
    judgments = InMemoryJudgmentStore()
    judgments.upsert(
        SuccessfulJudgment(
            ticker=Ticker("7203.T"),
            as_of=PAST,
            score=62,
            label=Label.BUY,
            reason="終値3200円付近で前日比高寄り。",
        )
    )
    runs = InMemoryDayRunStore()
    runs.save(
        PAST,
        DailyRunResult(
            market_closed=False,
            outcomes=(
                SuccessfulJudgment(
                    ticker=Ticker("7203.T"),
                    as_of=PAST,
                    score=62,
                    label=Label.BUY,
                    reason="終値3200円付近で前日比高寄り。",
                ),
                FailedJudgment(
                    ticker=Ticker("9999.T"),
                    as_of=PAST,
                    kind=FailureKind.UNAVAILABLE,
                ),
            ),
        ),
    )
    app = create_app(
        InMemoryInstrumentStore(),
        judgments=judgments,
        runs=runs,
        market=FakeMarketData(),
        model=FakeJudgmentModel(),
        today=lambda: TODAY,
    )
    client = TestClient(app)

    response = client.get("/", params={"history_as_of": PAST.isoformat()})

    assert 'aria-label="7203.T 買う スコア62"' in response.text
    assert "9999.T" not in response.text
    assert "取得不可" not in response.text
