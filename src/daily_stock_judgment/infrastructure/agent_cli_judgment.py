"""JudgmentModel via a configurable local agent CLI (no product hardcoding)."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind, JudgmentDraft
from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.agent_prompt import build_prompt

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class CliRunResult:
    stdout: str
    exit_code: int
    timed_out: bool = False


CliRunner = Callable[[Sequence[str], str], CliRunResult]


def run_cli_subprocess(
    command: Sequence[str],
    prompt: str,
    *,
    timeout_seconds: float,
) -> CliRunResult:
    try:
        completed = subprocess.run(
            list(command),
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CliRunResult(stdout="", exit_code=-1, timed_out=True)
    except OSError:
        return CliRunResult(stdout="", exit_code=-1, timed_out=False)
    return CliRunResult(stdout=completed.stdout or "", exit_code=completed.returncode)


def parse_judgment_json(raw: str, *, expected_ticker: str) -> Result[JudgmentDraft, str]:
    text = raw.strip()
    if not text:
        return Err("empty CLI output")
    match = _JSON_OBJECT.search(text)
    if match is None:
        return Err("no JSON object in CLI output")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Err("invalid JSON")
    if not isinstance(payload, dict):
        return Err("JSON root must be an object")
    ticker = payload.get("ticker")
    score = payload.get("score")
    reason = payload.get("reason")
    if ticker != expected_ticker:
        return Err("ticker mismatch")
    if not isinstance(score, int) or isinstance(score, bool):
        return Err("score must be an integer")
    if not isinstance(reason, str):
        return Err("reason must be a string")
    # Ignore unknown keys (including label); system labeling owns that field.
    return Ok(JudgmentDraft(score=score, reason=reason))


class AgentCliJudgmentModel:
    """Invoke an operator-chosen CLI; prompt on stdin, JSON on stdout."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        run: CliRunner | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        if not command:
            raise ValueError("agent CLI command must not be empty")
        self._command = tuple(command)
        self._timeout_seconds = timeout_seconds
        self._run = run or (
            lambda cmd, prompt: run_cli_subprocess(
                cmd, prompt, timeout_seconds=timeout_seconds
            )
        )

    @classmethod
    def from_command_string(
        cls,
        command: str,
        *,
        run: CliRunner | None = None,
        timeout_seconds: float = 120.0,
    ) -> AgentCliJudgmentModel:
        return cls(
            shlex.split(command),
            run=run,
            timeout_seconds=timeout_seconds,
        )

    def draft(
        self,
        ticker: Ticker,
        as_of: date,
        is_holding: bool,
        bars: tuple[Bar, ...],
    ) -> Result[JudgmentDraft, FailureKind]:
        prompt = build_prompt(
            ticker=ticker, as_of=as_of, is_holding=is_holding, bars=bars
        )
        result = self._run(self._command, prompt)
        if result.timed_out or result.exit_code != 0:
            return Err(FailureKind.JUDGMENT_FAILED)
        parsed = parse_judgment_json(result.stdout, expected_ticker=ticker.value)
        if isinstance(parsed, Err):
            return Err(FailureKind.JUDGMENT_FAILED)
        return Ok(parsed.value)
