from __future__ import annotations

import sqlite3
from pathlib import Path

from daily_stock_judgment.domain.holding import Holding
from daily_stock_judgment.domain.ticker import Ticker
from daily_stock_judgment.domain.watchlist import replace_ticker


class SqliteInstrumentStore:
    """SQLite-backed InstrumentBook."""

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

    def list_watchlist(self) -> tuple[Ticker, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ticker FROM watchlist ORDER BY ticker"
            ).fetchall()
        return tuple(Ticker(row["ticker"]) for row in rows)

    def add_to_watchlist(self, ticker: Ticker) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)",
                (ticker.value,),
            )

    def remove_from_watchlist(self, ticker: Ticker) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM watchlist WHERE ticker = ?", (ticker.value,)
            )

    def replace_watchlist_ticker(self, old: Ticker, new: Ticker) -> None:
        current = frozenset(self.list_watchlist())
        updated = replace_ticker(current, old, new)
        with self._connect() as conn:
            conn.execute("DELETE FROM watchlist")
            conn.executemany(
                "INSERT INTO watchlist (ticker) VALUES (?)",
                [(t.value,) for t in sorted(updated)],
            )

    def list_holdings(self) -> tuple[Holding, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ticker, quantity FROM holdings ORDER BY ticker"
            ).fetchall()
        return tuple(
            Holding(ticker=Ticker(row["ticker"]), quantity=row["quantity"])
            for row in rows
        )

    def upsert_holding(self, holding: Holding) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO holdings (ticker, quantity) VALUES (?, ?)
                ON CONFLICT(ticker) DO UPDATE SET quantity = excluded.quantity
                """,
                (holding.ticker.value, holding.quantity),
            )

    def remove_holding(self, ticker: Ticker) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM holdings WHERE ticker = ?", (ticker.value,)
            )
