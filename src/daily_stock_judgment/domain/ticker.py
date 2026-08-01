from __future__ import annotations

import re
from dataclasses import dataclass

from daily_stock_judgment.domain.result import Err, Ok, Result

_TICKER_RE = re.compile(r"^[0-9A-Z]+\.T$")


@dataclass(frozen=True, order=True)
class Ticker:
    """Japan Yahoo Finance equity symbol (e.g. 7203.T)."""

    value: str

    def __str__(self) -> str:
        return self.value


def parse_ticker(raw: str) -> Result[Ticker, str]:
    cleaned = raw.strip().upper()
    if not cleaned:
        return Err("ticker must not be empty")
    if not _TICKER_RE.match(cleaned):
        return Err("ticker must be a Japan Yahoo symbol like 7203.T")
    return Ok(Ticker(cleaned))
