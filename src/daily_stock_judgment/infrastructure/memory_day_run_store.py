from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from daily_stock_judgment.application.run_daily_judgment import DailyRunResult


@dataclass(frozen=True)
class _State:
    runs: frozenset[tuple[date, DailyRunResult]] = frozenset()


class InMemoryDayRunStore:
    """Immutable in-memory DayRunStore for tests."""

    def __init__(self) -> None:
        self._state = _State()

    def save(self, as_of: date, result: DailyRunResult) -> None:
        without = frozenset(
            (d, r) for (d, r) in self._state.runs if d != as_of
        )
        self._state = replace(self._state, runs=without | {(as_of, result)})

    def load(self, as_of: date) -> DailyRunResult | None:
        for day, result in self._state.runs:
            if day == as_of:
                return result
        return None
