"""yfinance 市場アダプタの契約（ネットワーク非依存の注入フェッチ）。"""

from __future__ import annotations

from datetime import date, timedelta

from daily_stock_judgment.application.ports import SessionStatus
from daily_stock_judgment.application.run_daily_judgment import run_daily_judgments
from daily_stock_judgment.domain.judgment import (
    FailedJudgment,
    FailureKind,
    JudgmentDraft,
    JudgmentTarget,
    SuccessfulJudgment,
)
from daily_stock_judgment.domain.result import Ok
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.memory_judgment_store import (
    InMemoryJudgmentStore,
)
from daily_stock_judgment.infrastructure.yfinance_market import (
    HistoryRow,
    YFinanceMarketData,
)
from tests.fake_adapters import FakeJudgmentModel

AS_OF = date(2026, 7, 31)


def _row(day: date, close: float = 100.0) -> HistoryRow:
    return HistoryRow(
        date=day,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1_000.0,
    )


def _rows_through(as_of: date, count: int) -> tuple[HistoryRow, ...]:
    return tuple(_row(as_of - timedelta(days=offset)) for offset in range(count - 1, -1, -1))


class _CaptureLens(FakeJudgmentModel):
    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.bar_lens: list[int] = []

    def draft(self, ticker, as_of, is_holding, bars):  # type: ignore[no-untyped-def]
        self.bar_lens.append(len(bars))
        return super().draft(ticker, as_of, is_holding, bars)


def test_ティッカーの日足が最大60本までランナーに渡る() -> None:
    series = _rows_through(AS_OF, 90)

    def fetch(symbol: str, start: date, end: date) -> tuple[HistoryRow, ...]:
        del symbol
        return tuple(r for r in series if start <= r.date <= end)

    market = YFinanceMarketData(fetch_history=fetch, session_probe="7203.T")
    model = _CaptureLens(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(score=10, reason="終値100円前後で横ばい。")
        }
    )
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
        store=InMemoryJudgmentStore(),
    )
    assert isinstance(result.outcomes[0], SuccessfulJudgment)
    assert model.bar_lens == [60]


def test_履歴が60未満でも取れた分だけで成功する() -> None:
    series = _rows_through(AS_OF, 4)

    def fetch(symbol: str, start: date, end: date) -> tuple[HistoryRow, ...]:
        del symbol
        return tuple(r for r in series if start <= r.date <= end)

    market = YFinanceMarketData(fetch_history=fetch, session_probe="7203.T")
    model = _CaptureLens(
        drafts_by_ticker={
            "7203.T": JudgmentDraft(score=10, reason="終値100円前後で横ばい。")
        }
    )
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
        store=InMemoryJudgmentStore(),
    )
    assert isinstance(result.outcomes[0], SuccessfulJudgment)
    assert model.bar_lens == [4]


def test_空の履歴は取得不可になりリトライしない() -> None:
    calls = {"n": 0}

    def fetch(symbol: str, start: date, end: date) -> tuple[HistoryRow, ...]:
        del start, end
        calls["n"] += 1
        if symbol == "7203.T":
            return (_row(AS_OF),)
        return ()

    market = YFinanceMarketData(fetch_history=fetch, session_probe="7203.T")
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("9999.T"), is_holding=False),),
        market=market,
        model=FakeJudgmentModel(),
        store=InMemoryJudgmentStore(),
    )
    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.UNAVAILABLE
    assert calls["n"] == 2


def test_当日バー未着はデータ未着でランナーが最大2回リトライする() -> None:
    calls = {"n": 0}

    def fetch(symbol: str, start: date, end: date) -> tuple[HistoryRow, ...]:
        del start, end
        calls["n"] += 1
        if symbol == "1306.T":
            return (_row(AS_OF),)
        return (_row(AS_OF - timedelta(days=1)),)

    market = YFinanceMarketData(fetch_history=fetch, session_probe="1306.T")
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=FakeJudgmentModel(),
        store=InMemoryJudgmentStore(),
    )
    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.DATA_MISSING
    assert calls["n"] == 4


def test_市場プローブに当日バーが無いとき休場扱いで判断しない() -> None:
    def fetch(symbol: str, start: date, end: date) -> tuple[HistoryRow, ...]:
        del symbol, start, end
        return (_row(AS_OF - timedelta(days=1)),)

    market = YFinanceMarketData(fetch_history=fetch, session_probe="1306.T")
    assert market.session_status(AS_OF) is SessionStatus.CLOSED
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=FakeJudgmentModel(
            drafts_by_ticker={
                "7203.T": JudgmentDraft(score=10, reason="終値100円前後で横ばい。")
            }
        ),
        store=InMemoryJudgmentStore(),
    )
    assert result.market_closed is True
    assert result.outcomes == ()


def test_セッション取得が例外のとき休場にせずオープン扱いになる() -> None:
    def fetch(symbol: str, start: date, end: date) -> tuple[HistoryRow, ...]:
        del symbol, start, end
        raise RuntimeError("yahoo down")

    market = YFinanceMarketData(fetch_history=fetch, session_probe="1306.T")
    assert market.session_status(AS_OF) is SessionStatus.OPEN


def test_bars_forは当日バーがあるときOkを返す() -> None:
    def fetch(symbol: str, start: date, end: date) -> tuple[HistoryRow, ...]:
        del symbol
        return (_row(AS_OF - timedelta(days=1)), _row(AS_OF, close=3067.0))

    market = YFinanceMarketData(fetch_history=fetch)
    result = market.bars_for(Ticker("7203.T"), AS_OF)
    assert isinstance(result, Ok)
    assert result.value[-1].close == 3067.0
    assert result.value[-1].date == AS_OF
    assert len(result.value) == 2
