from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from daily_stock_judgment.application.run_daily_judgment import DailyRunResult
from daily_stock_judgment.domain.judgment import (
    FailedJudgment,
    FailureKind,
    Label,
    SuccessfulJudgment,
)
from daily_stock_judgment.domain.ticker import Ticker


class SqliteDayRunStore:
    """SQLite snapshot of the last full run per as_of (includes failures)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS day_runs (
                    as_of TEXT PRIMARY KEY,
                    market_closed INTEGER NOT NULL,
                    outcomes_json TEXT NOT NULL
                )
                """
            )

    def save(self, as_of: date, result: DailyRunResult) -> None:
        payload = [_outcome_to_dict(o) for o in result.outcomes]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO day_runs (as_of, market_closed, outcomes_json)
                VALUES (?, ?, ?)
                ON CONFLICT(as_of) DO UPDATE SET
                    market_closed = excluded.market_closed,
                    outcomes_json = excluded.outcomes_json
                """,
                (
                    as_of.isoformat(),
                    1 if result.market_closed else 0,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def load(self, as_of: date) -> DailyRunResult | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT market_closed, outcomes_json
                FROM day_runs
                WHERE as_of = ?
                """,
                (as_of.isoformat(),),
            ).fetchone()
        if row is None:
            return None
        outcomes = tuple(
            _outcome_from_dict(item) for item in json.loads(row["outcomes_json"])
        )
        return DailyRunResult(
            market_closed=bool(row["market_closed"]),
            outcomes=outcomes,
        )


def _outcome_to_dict(outcome: SuccessfulJudgment | FailedJudgment) -> dict:
    if isinstance(outcome, SuccessfulJudgment):
        return {
            "ok": True,
            "ticker": outcome.ticker.value,
            "as_of": outcome.as_of.isoformat(),
            "score": outcome.score,
            "label": outcome.label.value,
            "reason": outcome.reason,
        }
    return {
        "ok": False,
        "ticker": outcome.ticker.value,
        "as_of": outcome.as_of.isoformat(),
        "kind": outcome.kind.value,
    }


def _outcome_from_dict(item: dict) -> SuccessfulJudgment | FailedJudgment:
    ticker = Ticker(item["ticker"])
    as_of = date.fromisoformat(item["as_of"])
    if item["ok"]:
        return SuccessfulJudgment(
            ticker=ticker,
            as_of=as_of,
            score=item["score"],
            label=Label(item["label"]),
            reason=item["reason"],
        )
    return FailedJudgment(
        ticker=ticker,
        as_of=as_of,
        kind=FailureKind(item["kind"]),
    )
