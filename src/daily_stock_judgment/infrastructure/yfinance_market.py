"""MarketDataSource backed by yfinance Japan daily OHLCV."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from daily_stock_judgment.application.ports import SessionStatus
from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.judgment import FailureKind
from daily_stock_judgment.domain.result import Err, Ok, Result
from daily_stock_judgment.domain.ticker import Ticker

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
        except Exception:
            # Network/Yahoo faults are not exchange holidays; let per-ticker fetch decide.
            return SessionStatus.OPEN
        if any(row.date == as_of for row in rows):
            return SessionStatus.OPEN
        return SessionStatus.CLOSED

    def bars_for(
        self, ticker: Ticker, as_of: date
    ) -> Result[tuple[Bar, ...], FailureKind]:
        try:
            rows = self._fetch_range(ticker.value, as_of)
        except Exception:
            return Err(FailureKind.UNAVAILABLE)
        if not rows:
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
            return Err(FailureKind.UNAVAILABLE)
        if capped[-1].date != as_of:
            return Err(FailureKind.DATA_MISSING)
        return Ok(capped)

    def _fetch_range(self, symbol: str, as_of: date) -> tuple[HistoryRow, ...]:
        start = as_of - timedelta(days=_LOOKBACK_CALENDAR_DAYS)
        return self._fetch(symbol, start, as_of)
