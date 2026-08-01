from __future__ import annotations

from daily_stock_judgment.domain.judgment import Label


def label_for(score: int, *, is_holding: bool) -> Label:
    """Fixed thresholds: ±50 inclusive; sell only when holding."""
    if score >= 50:
        return Label.BUY
    if score <= -50:
        return Label.SELL if is_holding else Label.WAIT
    return Label.WAIT
