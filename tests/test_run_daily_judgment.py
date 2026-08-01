"""日次判断ランナー境界（仕様 Testing Decisions の主 seam）。

差し替え: FakeMarketData / FakeJudgmentModel / InMemoryJudgmentStore。
SQLite スキーマや CLI 引数には依存しない。
"""

from __future__ import annotations

from datetime import date

from daily_stock_judgment.application.run_daily_judgment import run_daily_judgments
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import (
    FailedJudgment,
    FailureKind,
    JudgmentDraft,
    JudgmentTarget,
    Label,
    SuccessfulJudgment,
)
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.memory_judgment_store import (
    InMemoryJudgmentStore,
)
from tests.fake_adapters import FakeJudgmentModel, FakeMarketData

AS_OF = date(2026, 7, 31)


def _bar(day: date, close: float = 100.0) -> Bar:
    return Bar(
        date=day,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000.0,
    )


def _run(
    *,
    targets: tuple[JudgmentTarget, ...],
    market: FakeMarketData,
    model: FakeJudgmentModel,
    store: InMemoryJudgmentStore | None = None,
):
    store = store or InMemoryJudgmentStore()
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=targets,
        market=market,
        model=model,
        store=store,
    )
    return result, store


def test_スコアが買い閾値以上のとき買うラベルと理由が結果に載る() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar(AS_OF, 3200.0)]})
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(
                score=62, reason="終値3200円付近で前日比高寄り。"
            )
        }
    )

    result, _ = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, SuccessfulJudgment)
    assert outcome.score == 62
    assert outcome.label is Label.BUY
    assert outcome.reason == "終値3200円付近で前日比高寄り。"


def test_未保有でスコアが売り閾値以下のとき様子見になる() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar(AS_OF)]})
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(
                score=-50, reason="終値は安寄りで前日比下落。"
            )
        }
    )

    result, _ = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, SuccessfulJudgment)
    assert outcome.label is Label.WAIT


def test_保有中でスコアが売り閾値以下のとき売るになる() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar(AS_OF)]})
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(
                score=-50, reason="終値は安寄りで前日比下落。"
            )
        }
    )

    result, _ = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=True),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, SuccessfulJudgment)
    assert outcome.label is Label.SELL


def test_一部銘柄が失敗しても他銘柄の成功判断は結果に残る() -> None:
    market = FakeMarketData(
        bars_by_ticker={"7203.T": [_bar(AS_OF)]},
        failure_by_ticker={"9999.T": FailureKind.UNAVAILABLE},
    )
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(score=10, reason="終値100円前後で横ばい。")
        }
    )

    result, store = _run(
        targets=(
            JudgmentTarget(Ticker("7203.T"), is_holding=False),
            JudgmentTarget(Ticker("9999.T"), is_holding=False),
        ),
        market=market,
        model=model,
    )

    assert isinstance(result.outcomes[0], SuccessfulJudgment)
    assert isinstance(result.outcomes[1], FailedJudgment)
    assert result.outcomes[1].kind is FailureKind.UNAVAILABLE
    assert len(store.list_for(AS_OF)) == 1


def test_当日バーが取れないときデータ未着になる() -> None:
    market = FakeMarketData(
        failure_by_ticker={"7203.T": FailureKind.DATA_MISSING},
    )
    model = FakeJudgmentModel()

    result, store = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.DATA_MISSING
    assert market.fetch_calls["7203.T"] == 3  # 初回 + リトライ2回
    assert store.list_for(AS_OF) == ()


def test_銘柄が取得できないとき取得不可になりリトライしない() -> None:
    market = FakeMarketData(
        failure_by_ticker={"7203.T": FailureKind.UNAVAILABLE},
    )
    model = FakeJudgmentModel()

    result, _ = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.UNAVAILABLE
    assert market.fetch_calls["7203.T"] == 1


def test_LLMが制約不合格のままのとき判断失敗になる() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar(AS_OF)]})
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": [
                JudgmentDraft(score=80, reason="買うべき局面。終値は高寄り。"),
                JudgmentDraft(score=80, reason="様子見が妥当。終値は高寄り。"),
            ]
        }
    )

    result, store = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.JUDGMENT_FAILED
    assert model.call_counts["7203.T"] == 2
    assert store.list_for(AS_OF) == ()


def test_休場日のとき新規判断を作らない() -> None:
    market = FakeMarketData(
        closed_days={AS_OF},
        bars_by_ticker={"7203.T": [_bar(AS_OF)]},
    )
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(score=62, reason="終値は高寄り。")
        }
    )
    store = InMemoryJudgmentStore()

    result, store = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
        store=store,
    )

    assert result.market_closed is True
    assert result.outcomes == ()
    assert store.list_for(AS_OF) == ()
    assert model.call_counts.get("7203.T", 0) == 0


def test_LLM呼び出しが二度失敗したとき判断失敗になる() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar(AS_OF)]})
    model = FakeJudgmentModel(call_failures_remaining={"7203.T": 2})

    result, store = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.JUDGMENT_FAILED
    assert model.call_counts["7203.T"] == 2
    assert store.list_for(AS_OF) == ()


def test_スコアと理由の向きが食い違うとき再生成後もダメなら判断失敗になる() -> None:
    market = FakeMarketData(bars_by_ticker={"7203.T": [_bar(AS_OF)]})
    model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": [
                JudgmentDraft(score=80, reason="終値は前日比で下落した。"),
                JudgmentDraft(score=80, reason="終値は安値圏へ沈んだ。"),
            ]
        }
    )

    result, store = _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
    )

    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.JUDGMENT_FAILED
    assert model.call_counts["7203.T"] == 2
    assert store.list_for(AS_OF) == ()


def test_成功した判断だけが保存され同日再実行で上書きされる() -> None:
    market = FakeMarketData(
        bars_by_ticker={
            "7203.T": [_bar(AS_OF)],
            "9999.T": [],  # unused; marked unavailable
        },
        failure_by_ticker={"9999.T": FailureKind.UNAVAILABLE},
    )
    store = InMemoryJudgmentStore()

    first_model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(score=10, reason="終値100円前後で横ばい。")
        }
    )
    _run(
        targets=(
            JudgmentTarget(Ticker("7203.T"), is_holding=False),
            JudgmentTarget(Ticker("9999.T"), is_holding=False),
        ),
        market=market,
        model=first_model,
        store=store,
    )

    second_model = FakeJudgmentModel(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(
                score=70, reason="終値は前日比で高寄りに転換。"
            )
        }
    )
    _run(
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=second_model,
        store=store,
    )

    saved = store.list_for(AS_OF)
    assert len(saved) == 1
    assert saved[0].score == 70
    assert saved[0].label is Label.BUY
