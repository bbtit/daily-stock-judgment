from __future__ import annotations

import re

from daily_stock_judgment.domain.judgment import JudgmentDraft, Label
from daily_stock_judgment.domain.result import Err, Ok, Result

_LABEL_WORDS = tuple(label.value for label in Label)
_MAX_REASON_LEN = 200
_CLOSE_OBSERVATION = re.compile(r"終値|前日比|高安")
_BULLISH = re.compile(r"上昇|高値|高寄り|買い優勢")
_BEARISH = re.compile(r"下落|安値|安寄り|売られ")


def validate_draft(draft: JudgmentDraft) -> Result[JudgmentDraft, str]:
    if not isinstance(draft.score, int) or isinstance(draft.score, bool):
        return Err("score must be an integer")
    if draft.score < -100 or draft.score > 100:
        return Err("score out of range")
    reason = draft.reason.strip()
    if not reason:
        return Err("reason must not be empty")
    if len(reason) > _MAX_REASON_LEN:
        return Err("reason too long")
    if any(word in reason for word in _LABEL_WORDS):
        return Err("reason must not contain label words")
    if not _CLOSE_OBSERVATION.search(reason):
        return Err("reason must observe close level or change")
    if draft.score > 0 and _BEARISH.search(reason) and not _BULLISH.search(reason):
        return Err("reason sign mismatches score")
    if draft.score < 0 and _BULLISH.search(reason) and not _BEARISH.search(reason):
        return Err("reason sign mismatches score")
    return Ok(JudgmentDraft(score=draft.score, reason=reason))
