"""JudgmentModel via a configurable local agent CLI (no product hardcoding)."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

import structlog

from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind, JudgmentDraft
from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.infrastructure.agent_prompt import build_prompt

logger = structlog.get_logger(__name__)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_PROMPT_LOG_LIMIT = 80


@dataclass(frozen=True)
class CliRunResult:
    stdout: str
    exit_code: int
    timed_out: bool = False
    stderr: str = ""


CliRunner = Callable[[Sequence[str], str], CliRunResult]

_PROMPT_PLACEHOLDER = "{prompt}"


def expand_command(
    command: Sequence[str], prompt: str
) -> tuple[tuple[str, ...], bool]:
    """Replace `{prompt}` in argv. Returns (argv, embedded)."""
    embedded = False
    expanded: list[str] = []
    for part in command:
        if _PROMPT_PLACEHOLDER in part:
            embedded = True
            expanded.append(part.replace(_PROMPT_PLACEHOLDER, prompt))
        else:
            expanded.append(part)
    return tuple(expanded), embedded


def run_cli_subprocess(
    command: Sequence[str],
    stdin_text: str,
    *,
    timeout_seconds: float,
) -> CliRunResult:
    try:
        completed = subprocess.run(
            list(command),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CliRunResult(stdout="", stderr="", exit_code=-1, timed_out=True)
    except OSError as exc:
        return CliRunResult(
            stdout="", stderr=str(exc), exit_code=-1, timed_out=False
        )
    return CliRunResult(
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        exit_code=completed.returncode,
    )


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
    """Invoke an operator-chosen CLI; JSON on stdout.

    If the command template contains `{prompt}`, it is substituted into argv
    and stdin is left empty. Otherwise the prompt is written to stdin.
    """

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
            lambda cmd, stdin_text: run_cli_subprocess(
                cmd, stdin_text, timeout_seconds=timeout_seconds
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
        argv, embedded = expand_command(self._command, prompt)
        stdin_text = "" if embedded else prompt
        logger.info(
            "agent_cli_start",
            ticker=ticker.value,
            template=shlex.join(self._command),
            embedded=embedded,
            prompt_chars=len(prompt),
            timeout_s=self._timeout_seconds,
        )
        logger.debug(
            "agent_cli_argv",
            ticker=ticker.value,
            argv=_argv_for_log(argv, embedded=embedded),
        )
        started = time.monotonic()
        result = self._run(argv, stdin_text)
        elapsed = time.monotonic() - started
        if result.timed_out or result.exit_code != 0:
            logger.warning(
                "agent_cli_failed",
                ticker=ticker.value,
                exit=result.exit_code,
                timed_out=result.timed_out,
                elapsed_s=round(elapsed, 1),
                stderr=_clip(result.stderr, 500),
                stdout=_clip(result.stdout, 500),
            )
            return Err(FailureKind.JUDGMENT_FAILED)
        # Some CLIs print diagnostics on stderr; prefer stdout, then combined.
        parsed = parse_judgment_json(result.stdout, expected_ticker=ticker.value)
        if isinstance(parsed, Err) and result.stderr:
            parsed = parse_judgment_json(
                f"{result.stdout}\n{result.stderr}",
                expected_ticker=ticker.value,
            )
        if isinstance(parsed, Err):
            logger.warning(
                "agent_cli_parse_failed",
                ticker=ticker.value,
                reason=parsed.error,
                elapsed_s=round(elapsed, 1),
                stdout=_clip(result.stdout, 500),
                stderr=_clip(result.stderr, 500),
            )
            return Err(FailureKind.JUDGMENT_FAILED)
        logger.info(
            "agent_cli_ok",
            ticker=ticker.value,
            score=parsed.value.score,
            elapsed_s=round(elapsed, 1),
            reason=_clip(parsed.value.reason, 120),
        )
        return Ok(parsed.value)


def _clip(text: str, limit: int) -> str:
    text = text.replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _argv_for_log(argv: Sequence[str], *, embedded: bool) -> str:
    if not embedded:
        return shlex.join(argv)
    redacted: list[str] = []
    for part in argv:
        if len(part) > _PROMPT_LOG_LIMIT and ("入力 JSON" in part or "\n" in part):
            redacted.append(f"<prompt {len(part)} chars>")
        else:
            redacted.append(part)
    return shlex.join(redacted)
