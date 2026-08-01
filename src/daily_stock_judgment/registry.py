from __future__ import annotations

import sqlite3
from pathlib import Path


class InstrumentRegistry:
    """SQLite-backed watchlist and holdings (保有)."""

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
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    ticker TEXT PRIMARY KEY COLLATE NOCASE
                );
                CREATE TABLE IF NOT EXISTS holdings (
                    ticker TEXT PRIMARY KEY COLLATE NOCASE,
                    quantity REAL
                );
                """
            )

    def add_to_watchlist(self, ticker: str) -> None:
        normalized = _normalize_ticker(ticker)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)",
                (normalized,),
            )

    def list_watchlist(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ticker FROM watchlist ORDER BY ticker"
            ).fetchall()
        return [row["ticker"] for row in rows]

    def remove_from_watchlist(self, ticker: str) -> None:
        normalized = _normalize_ticker(ticker)
        with self._connect() as conn:
            conn.execute("DELETE FROM watchlist WHERE ticker = ?", (normalized,))

    def register_holding(
        self, ticker: str, quantity: float | None = None
    ) -> None:
        normalized = _normalize_ticker(ticker)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO holdings (ticker, quantity) VALUES (?, ?)
                ON CONFLICT(ticker) DO UPDATE SET quantity = excluded.quantity
                """,
                (normalized, quantity),
            )

    def list_holdings(self) -> list[dict[str, float | str | None]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ticker, quantity FROM holdings ORDER BY ticker"
            ).fetchall()
        return [
            {"ticker": row["ticker"], "quantity": row["quantity"]} for row in rows
        ]

    def unregister_holding(self, ticker: str) -> None:
        normalized = _normalize_ticker(ticker)
        with self._connect() as conn:
            conn.execute("DELETE FROM holdings WHERE ticker = ?", (normalized,))


def _normalize_ticker(ticker: str) -> str:
    cleaned = ticker.strip().upper()
    if not cleaned:
        raise ValueError("ticker must not be empty")
    return cleaned
