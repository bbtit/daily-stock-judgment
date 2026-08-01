"""MarketDataSource backed by yfinance Japan daily OHLCV."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from daily_stock_judgment.application.ports import SessionStatus
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind
from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker

logger = logging.getLogger(__name__)

# Calendar span long enough to cover ~60 trading days plus holidays.
_LOOKBACK_CALENDAR_DAYS = 120
_MAX_BARS = 60
# Liquid TOPIX ETF used to detect exchange-wide closed sessions.
_DEFAULT_SESSION_PROBE = "1306.T"

HistoryFetcher = Callable[[str, date, date], tuple["HistoryRow", ...]]


@dataclass(frozen=True)
class HistoryRow:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


def fetch_history_via_yfinance(
    symbol: str, start: date, end: date
) -> tuple[HistoryRow, ...]:
    """Default network fetch. `end` is inclusive."""
    import yfinance as yf

    frame = yf.Ticker(symbol).history(
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=False,
        actions=False,
    )
    if frame is None or frame.empty:
        return ()

    rows: list[HistoryRow] = []
    for idx, row in frame.iterrows():
        day = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
        rows.append(
            HistoryRow(
                date=day,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )
    return tuple(rows)


class YFinanceMarketData:
    """Japan equity daily bars from yfinance (.T tickers)."""

    def __init__(
        self,
        *,
        fetch_history: HistoryFetcher | None = None,
        session_probe: str = _DEFAULT_SESSION_PROBE,
    ) -> None:
        self._fetch = fetch_history or fetch_history_via_yfinance
        self._session_probe = session_probe

    def session_status(self, as_of: date) -> SessionStatus:
        try:
            rows = self._fetch_range(self._session_probe, as_of)
        except Exception as exc:
            # Network/Yahoo faults are not exchange holidays; let per-ticker fetch decide.
            logger.warning(
                "session probe error as_of=%s probe=%s err=%s; treating as OPEN",
                as_of.isoformat(),
                self._session_probe,
                exc,
            )
            return SessionStatus.OPEN
        if any(row.date == as_of for row in rows):
            logger.info(
                "session OPEN as_of=%s probe=%s rows=%d",
                as_of.isoformat(),
                self._session_probe,
                len(rows),
            )
            return SessionStatus.OPEN
        last = rows[-1].date.isoformat() if rows else "-"
        logger.info(
            "session CLOSED as_of=%s probe=%s rows=%d last_bar=%s",
            as_of.isoformat(),
            self._session_probe,
            len(rows),
            last,
        )
        return SessionStatus.CLOSED

    def bars_for(
        self, ticker: Ticker, as_of: date
    ) -> Result[tuple[Bar, ...], FailureKind]:
        try:
            rows = self._fetch_range(ticker.value, as_of)
        except Exception as exc:
            logger.warning(
                "yfinance fetch error ticker=%s as_of=%s err=%s",
                ticker.value,
                as_of.isoformat(),
                exc,
            )
            return Err(FailureKind.UNAVAILABLE)
        if not rows:
            logger.warning(
                "yfinance empty ticker=%s as_of=%s",
                ticker.value,
                as_of.isoformat(),
            )
            return Err(FailureKind.UNAVAILABLE)

        capped = tuple(
            Bar(
                date=row.date,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in rows
            if row.date <= as_of
        )[-_MAX_BARS:]
        if not capped:
            logger.warning(
                "yfinance no bars <= as_of ticker=%s as_of=%s raw_rows=%d",
                ticker.value,
                as_of.isoformat(),
                len(rows),
            )
            return Err(FailureKind.UNAVAILABLE)
        if capped[-1].date != as_of:
            logger.info(
                "yfinance DATA_MISSING ticker=%s as_of=%s last_bar=%s count=%d",
                ticker.value,
                as_of.isoformat(),
                capped[-1].date.isoformat(),
                len(capped),
            )
            return Err(FailureKind.DATA_MISSING)
        return Ok(capped)

    def _fetch_range(self, symbol: str, as_of: date) -> tuple[HistoryRow, ...]:
        start = as_of - timedelta(days=_LOOKBACK_CALENDAR_DAYS)
        return self._fetch(symbol, start, as_of)
