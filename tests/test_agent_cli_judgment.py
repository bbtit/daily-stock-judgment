"""エージェント CLI JudgmentModel の契約（CLI 実行は注入）。"""

from __future__ import annotations

import json
from datetime import date

from daily_stock_judgment.application.run_daily_judgment import run_daily_judgments
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import (
    FailedJudgment,
    FailureKind,
    JudgmentTarget,
    SuccessfulJudgment,
)
from daily_stock_judgment.domain.result import Ok
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.agent_cli_judgment import (
    AgentCliJudgmentModel,
    CliRunResult,
    parse_judgment_json,
)
from daily_stock_judgment.infrastructure.agent_prompt import build_prompt
from daily_stock_judgment.infrastructure.memory_judgment_store import (
    InMemoryJudgmentStore,
)
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


def test_プロンプトに1銘柄分の入力JSONが載る() -> None:
    prompt = build_prompt(
        ticker=Ticker("7203.T"),
        as_of=AS_OF,
        is_holding=True,
        bars=BARS,
    )
    assert "入力 JSON:" in prompt
    assert '"ticker":"7203.T"' in prompt or '"ticker": "7203.T"' in prompt
    payload = json.loads(prompt.split("入力 JSON:\n", 1)[1])
    assert payload == {
        "ticker": "7203.T",
        "as_of": "2026-07-31",
        "is_holding": True,
        "bars": [
            {
                "date": "2026-07-31",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000.0,
            }
        ],
    }
    assert "label" not in payload
    assert "買う" in prompt  # instruction forbids label words in reason


def test_正常JSONをパースしてscoreとreasonが取れる() -> None:
    parsed = parse_judgment_json(
        '前置\n{"ticker":"7203.T","score":62,"reason":"終値は前日比で高寄り。"}\n',
        expected_ticker="7203.T",
    )
    assert isinstance(parsed, Ok)
    assert parsed.value.score == 62
    assert parsed.value.reason == "終値は前日比で高寄り。"


def test_CLIが正常JSONを返したときランナーで買うラベルが付く() -> None:
    def run(command, prompt: str) -> CliRunResult:
        assert command == ("my-agent", "--once")
        assert '"ticker":"7203.T"' in prompt.replace(" ", "")
        return CliRunResult(
            stdout='{"ticker":"7203.T","score":62,"reason":"終値は前日比で高寄り。"}',
            exit_code=0,
        )

    model = AgentCliJudgmentModel(("my-agent", "--once"), run=run)
    market = FakeMarketData(bars_by_ticker={"7203.T": list(BARS)})
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
        store=InMemoryJudgmentStore(),
    )
    outcome = result.outcomes[0]
    assert isinstance(outcome, SuccessfulJudgment)
    assert outcome.score == 62
    assert outcome.label.value == "買う"


def test_不正JSONのとき呼び出し失敗としてリトライ後に判断失敗になる() -> None:
    calls = {"n": 0}

    def run(command, prompt: str) -> CliRunResult:
        del command, prompt
        calls["n"] += 1
        return CliRunResult(stdout="not-json", exit_code=0)

    model = AgentCliJudgmentModel(("agent",), run=run)
    market = FakeMarketData(bars_by_ticker={"7203.T": list(BARS)})
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
        store=InMemoryJudgmentStore(),
    )
    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.JUDGMENT_FAILED
    assert calls["n"] == 2


def test_CLIが非ゼロ終了のとき呼び出し失敗としてリトライ後に判断失敗になる() -> None:
    calls = {"n": 0}

    def run(command, prompt: str) -> CliRunResult:
        del command, prompt
        calls["n"] += 1
        return CliRunResult(stdout="", exit_code=2)

    model = AgentCliJudgmentModel(("agent",), run=run)
    market = FakeMarketData(bars_by_ticker={"7203.T": list(BARS)})
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
        store=InMemoryJudgmentStore(),
    )
    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.JUDGMENT_FAILED
    assert calls["n"] == 2


def test_タイムアウトのとき判断失敗になる() -> None:
    def run(command, prompt: str) -> CliRunResult:
        del command, prompt
        return CliRunResult(stdout="", exit_code=-1, timed_out=True)

    model = AgentCliJudgmentModel(("agent",), run=run)
    draft = model.draft(Ticker("7203.T"), AS_OF, False, BARS)
    assert draft.error is FailureKind.JUDGMENT_FAILED


def test_符号不一致理由は再生成後もダメなら判断失敗になる() -> None:
    replies = [
        '{"ticker":"7203.T","score":80,"reason":"終値は前日比で下落した。"}',
        '{"ticker":"7203.T","score":80,"reason":"終値は安値圏へ沈んだ。"}',
    ]

    def run(command, prompt: str) -> CliRunResult:
        del command, prompt
        return CliRunResult(stdout=replies.pop(0), exit_code=0)

    model = AgentCliJudgmentModel(("agent",), run=run)
    market = FakeMarketData(bars_by_ticker={"7203.T": list(BARS)})
    result = run_daily_judgments(
        as_of=AS_OF,
        targets=(JudgmentTarget(Ticker("7203.T"), is_holding=False),),
        market=market,
        model=model,
        store=InMemoryJudgmentStore(),
    )
    outcome = result.outcomes[0]
    assert isinstance(outcome, FailedJudgment)
    assert outcome.kind is FailureKind.JUDGMENT_FAILED
    assert replies == []


def test_コマンド文字列から製品固定なしで組み立てられる() -> None:
    seen: list[tuple[str, ...]] = []

    def run(command, prompt: str) -> CliRunResult:
        del prompt
        seen.append(tuple(command))
        return CliRunResult(
            stdout='{"ticker":"7203.T","score":10,"reason":"終値100円前後。"}',
            exit_code=0,
        )

    model = AgentCliJudgmentModel.from_command_string(
        "fancy-cli --json", run=run
    )
    assert isinstance(model.draft(Ticker("7203.T"), AS_OF, False, BARS), Ok)
    assert seen == [("fancy-cli", "--json")]
