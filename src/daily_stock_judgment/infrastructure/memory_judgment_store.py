from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from daily_stock_judgment.domain.judgment import SuccessfulJudgment


@dataclass(frozen=True)
class _State:
    rows: frozenset[SuccessfulJudgment] = frozenset()


class InMemoryJudgmentStore:
    """Immutable in-memory JudgmentBook for tests."""

    def __init__(self) -> None:
        self._state = _State()

    def upsert(self, judgment: SuccessfulJudgment) -> None:
        without = frozenset(
            j
            for j in self._state.rows
            if not (j.ticker == judgment.ticker and j.as_of == judgment.as_of)
        )
        self._state = replace(self._state, rows=without | {judgment})

    def list_for(self, as_of: date) -> tuple[SuccessfulJudgment, ...]:
        items = [j for j in self._state.rows if j.as_of == as_of]
        return tuple(sorted(items, key=lambda j: j.ticker.value))
