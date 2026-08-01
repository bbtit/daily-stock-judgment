"""判断ランのログがデバッグに使えること。"""

from __future__ import annotations

import logging
from datetime import date

import pytest

from daily_stock_judgment.application.run_daily_judgment import run_daily_judgments
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind, JudgmentTarget
from daily_stock_judgment.domain.result import Err
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.agent_cli_judgment import (
    AgentCliJudgmentModel,
    CliRunResult,
)
from daily_stock_judgment.infrastructure.memory_judgment_store import (
    InMemoryJudgmentStore,
)
from daily_stock_judgment.logging_config import configure_logging
from tests.fake_adapters import FakeMarketData

AS_OF = date(2026, 7, 31)
BARS = (
    Bar(
        date=AS_OF,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000.0,
    ),
)


def test_パッケージロガーを設定できる() -> None:
    configure_logging("DEBUG")
    package = logging.getLogger("daily_stock_judgment")
    assert package.level == logging.DEBUG
    assert package.handlers
    assert package.propagate is False


def test_agent_CLI失敗時にexitとstderrがwarningに出る(
    caplog: pytest.LogCaptureFixture,
) -> None:
    model = AgentCliJudgmentModel(
        ("agent", "-p", "{prompt}"),
        run=lambda _cmd, _stdin: CliRunResult(
            stdout="",
            stderr="workspace not trusted",
            exit_code=1,
        ),
    )
    with caplog.at_level(
        logging.INFO, logger="daily_stock_judgment.infrastructure.agent_cli_judgment"
    ):
        result = model.draft(Ticker("7203.T"), AS_OF, True, BARS)
    assert isinstance(result, Err)
    assert result.error is FailureKind.JUDGMENT_FAILED
    assert "agent CLI failed" in caplog.text
    assert "exit=1" in caplog.text
    assert "workspace not trusted" in caplog.text


def test_ラン要約ログに成功失敗件数が出る(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = InMemoryJudgmentStore()
    market = FakeMarketData(bars_by_ticker={"7203.T": list(BARS)})
    model = AgentCliJudgmentModel(
        ("agent",),
        run=lambda _cmd, _stdin: CliRunResult(
            stdout="not-json",
            stderr="",
            exit_code=0,
        ),
    )
    with caplog.at_level(
        logging.INFO, logger="daily_stock_judgment.application.run_daily_judgment"
    ):
        run_daily_judgments(
            as_of=AS_OF,
            targets=(JudgmentTarget(ticker=Ticker("7203.T"), is_holding=True),),
            market=market,
            model=model,
            store=store,
        )
    assert "run start as_of=2026-07-31 targets=1" in caplog.text
    assert "outcome fail ticker=7203.T kind=判断失敗" in caplog.text
    assert "run done as_of=2026-07-31 ok=0 failed=1" in caplog.text
