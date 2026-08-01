from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from daily_stock_judgment.domain.judgment import Label, SuccessfulJudgment
from daily_stock_judgment.domain.ticker import Ticker


class SqliteJudgmentStore:
    """SQLite-backed JudgmentBook (successful judgments only)."""

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
                CREATE TABLE IF NOT EXISTS judgments (
                    ticker TEXT NOT NULL COLLATE NOCASE,
                    as_of TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    PRIMARY KEY (ticker, as_of)
                )
                """
            )

    def upsert(self, judgment: SuccessfulJudgment) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO judgments (ticker, as_of, score, label, reason)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ticker, as_of) DO UPDATE SET
                    score = excluded.score,
                    label = excluded.label,
                    reason = excluded.reason
                """,
                (
                    judgment.ticker.value,
                    judgment.as_of.isoformat(),
                    judgment.score,
                    judgment.label.value,
                    judgment.reason,
                ),
            )

    def list_for(self, as_of: date) -> tuple[SuccessfulJudgment, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ticker, as_of, score, label, reason
                FROM judgments
                WHERE as_of = ?
                ORDER BY ticker
                """,
                (as_of.isoformat(),),
            ).fetchall()
        return tuple(
            SuccessfulJudgment(
                ticker=Ticker(row["ticker"]),
                as_of=date.fromisoformat(row["as_of"]),
                score=row["score"],
                label=Label(row["label"]),
                reason=row["reason"],
            )
            for row in rows
        )
