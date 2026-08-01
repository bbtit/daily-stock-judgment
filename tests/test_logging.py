"""構造化ログと HTTP trace_id の振る舞い。"""

from __future__ import annotations

import json
import logging
from datetime import date

import pytest
import structlog
from fastapi.testclient import TestClient

from daily_stock_judgment.application.run_daily_judgment import run_daily_judgments
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind, JudgmentTarget
from daily_stock_judgment.domain.result import Err
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.agent_cli_judgment import (
    AgentCliJudgmentModel,
    CliRunResult,
)
from daily_stock_judgment.infrastructure.memory_day_run_store import (
    InMemoryDayRunStore,
)
from daily_stock_judgment.infrastructure.memory_instrument_store import (
    InMemoryInstrumentStore,
)
from daily_stock_judgment.infrastructure.memory_judgment_store import (
    InMemoryJudgmentStore,
)
from daily_stock_judgment.logging_config import (
    configure_logging,
    reset_logging_for_tests,
)
from daily_stock_judgment.presentation.web import create_app
from tests.fake_adapters import FakeJudgmentModel, FakeMarketData

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


@pytest.fixture(autouse=True)
def _fresh_logging() -> None:
    reset_logging_for_tests()
    yield
    reset_logging_for_tests()
    structlog.contextvars.clear_contextvars()


def _json_lines(stderr: str) -> list[dict]:
    rows: list[dict] = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        rows.append(json.loads(line))
    return rows


def _by_event(payloads: list[dict], event: str) -> list[dict]:
    return [p for p in payloads if p.get("event") == event]


def test_パッケージロガーをJSONで設定できる(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("DEBUG")
    package = logging.getLogger("daily_stock_judgment")
    assert package.level == logging.DEBUG
    assert package.handlers
    assert package.propagate is False

    log = structlog.get_logger("daily_stock_judgment.test")
    log.info("sample_event", ticker="7203.T")
    payloads = _json_lines(capsys.readouterr().err)
    assert payloads
    payload = payloads[-1]
    assert payload["event"] == "sample_event"
    assert payload["ticker"] == "7203.T"
    assert "trace_id" not in payload


def test_agent_CLI失敗時にexitとstderrがwarningに出る(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    model = AgentCliJudgmentModel(
        ("agent", "-p", "{prompt}"),
        run=lambda _cmd, _stdin: CliRunResult(
            stdout="",
            stderr="workspace not trusted",
            exit_code=1,
        ),
    )
    capsys.readouterr()
    result = model.draft(Ticker("7203.T"), AS_OF, True, BARS)
    assert isinstance(result, Err)
    assert result.error is FailureKind.JUDGMENT_FAILED
    failed = _by_event(_json_lines(capsys.readouterr().err), "agent_cli_failed")
    assert len(failed) == 1
    assert failed[0]["exit"] == 1
    assert failed[0]["stderr"] == "workspace not trusted"
    assert failed[0]["ticker"] == "7203.T"


def test_ラン要約ログに成功失敗件数が出る(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
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
    capsys.readouterr()
    run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(ticker=Ticker("7203.T"), is_holding=True),),
        market=market,
        model=model,
        store=store,
    )
    payloads = _json_lines(capsys.readouterr().err)
    starts = _by_event(payloads, "run_start")
    fails = _by_event(payloads, "outcome_fail")
    dones = _by_event(payloads, "run_done")
    assert starts[0]["as_of"] == "2026-07-31"
    assert starts[0]["targets"] == 1
    assert fails[0]["ticker"] == "7203.T"
    assert fails[0]["kind"] == "判断失敗"
    assert dones[0]["ok"] == 0
    assert dones[0]["failed"] == 1


def test_HTTPリクエストにtrace_idが付きレスポンスヘッダとログで一致する(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    app = create_app(
        InMemoryInstrumentStore(),
        judgments=InMemoryJudgmentStore(),
        runs=InMemoryDayRunStore(),
        market=FakeMarketData(),
        model=FakeJudgmentModel(),
        today=lambda: AS_OF,
    )
    capsys.readouterr()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    trace_id = response.headers["X-Trace-Id"]
    assert len(trace_id) == 32
    assert trace_id == trace_id.lower()
    assert all(c in "0123456789abcdef" for c in trace_id)

    payloads = _json_lines(capsys.readouterr().err)
    starts = _by_event(payloads, "http_request_start")
    ends = _by_event(payloads, "http_request_end")
    assert len(starts) == 1
    assert len(ends) == 1
    assert starts[0]["trace_id"] == trace_id
    assert starts[0]["http.request.method"] == "GET"
    assert starts[0]["url.path"] == "/"
    assert ends[0]["trace_id"] == trace_id
    assert ends[0]["http.response.status_code"] == 200
    assert "duration_ms" in ends[0]
