from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Bar:
    """One Japan equity daily OHLCV bar."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
