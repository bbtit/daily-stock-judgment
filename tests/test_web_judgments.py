"""今日の判断一覧 / 手動実行の HTTP seam。"""

from __future__ import annotations

import re
from datetime import date

from fastapi.testclient import TestClient

from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind, JudgmentDraft
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

AS_OF = date(2026, 7, 31)


def _bar(day: date = AS_OF) -> Bar:
    return Bar(
        date=day,
        open=100.0,
        high=100.0,
        low=100.0,
        close=100.0,
        volume=1_000.0,
    )


def _client(
    *,
    market: FakeMarketData,
    model: FakeJudgmentModel,
    book: InMemoryInstrumentStore | None = None,
    judgments: InMemoryJudgmentStore | None = None,
    runs: InMemoryDayRunStore | None = None,
) -> TestClient:
    book = book or InMemoryInstrumentStore()
    judgments = judgments or InMemoryJudgmentStore()
    runs = runs or InMemoryDayRunStore()
    app = create_app(
        book,
        judgments=judgments,
        runs=runs,
        market=market,
        model=model,
        today=lambda: AS_OF,
    )
    return TestClient(app)


def test_判断を実行したとき成功行にスコアラベル理由が表示される() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar()]})
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(
                score=62, reason="終値3200円付近で前日比高寄り。"
            )
        }
    )
    client = _client(market=market, model=model)
    client.post("/watchlist", data={"ticker": "7203.T"})

    response = client.post("/judgments/run", follow_redirects=True)

    assert response.status_code == 200
    assert 'aria-label="7203.T 買う スコア62"' in response.text
    assert "終値3200円付近で前日比高寄り。" in response.text


def test_失敗した銘柄は区分だけが表示されスコアは出ない() -> None:
    market = FakeMarketData(
        bars_by_ticker={"7203.T": [_bar()]},
        failure_by_ticker={"9999.T": FailureKind.UNAVAILABLE},
    )
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(score=10, reason="終値100円前後で横ばい。")
        }
    )
    client = _client(market=market, model=model)
    client.post("/watchlist", data={"ticker": "7203.T"})
    client.post("/watchlist", data={"ticker": "9999.T"})

    response = client.post("/judgments/run", follow_redirects=True)

    match = re.search(
        r'aria-label="9999\.T 取得不可"',
        response.text,
    )
    assert match is not None
    # Failure row content: only kind, no score/label fields in the li body.
    li = re.search(
        r'<li[^>]*aria-label="9999\.T 取得不可"[^>]*>(.*?)</li>',
        response.text,
        re.S,
    )
    assert li is not None
    assert "スコア" not in li.group(1)
    assert "買う" not in li.group(1)
    assert "様子見" not in li.group(1)
    assert "取得不可" in li.group(1)


def test_同日再実行したとき成功結果が画面に反映される() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar()]})
    client = _client(
        market=market,
        model=FakeJudgmentModel(
            drafts_by_ticker={
                "7203.T": JudgmentDraft(
                    score=10, reason="終値100円前後で横ばい。"
                )
            }
        ),
    )
    client.post("/watchlist", data={"ticker": "7203.T"})
    first = client.post("/judgments/run", follow_redirects=True)
    assert 'aria-label="7203.T 様子見 スコア10"' in first.text

    client.app.state.model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(
                score=70, reason="終値は前日比で高寄りに転換。"
            )
        }
    )
    second = client.post("/judgments/run", follow_redirects=True)
    assert 'aria-label="7203.T 買う スコア70"' in second.text
    assert "終値は前日比で高寄りに転換。" in second.text


def test_再読込しても失敗行が区分のみで残る() -> None:
    market = FakeMarketData(
        failure_by_ticker={"9999.T": FailureKind.DATA_MISSING},
    )
    client = _client(market=market, model=FakeJudgmentModel())
    client.post("/watchlist", data={"ticker": "9999.T"})
    client.post("/judgments/run", follow_redirects=True)

    reloaded = client.get("/")
    assert 'aria-label="9999.T データ未着"' in reloaded.text
    li = re.search(
        r'<li[^>]*aria-label="9999\.T データ未着"[^>]*>(.*?)</li>',
        reloaded.text,
        re.S,
    )
    assert li is not None
    assert "スコア" not in li.group(1)
