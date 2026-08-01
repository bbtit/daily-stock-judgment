"""Fixed prompt block + per-ticker input JSON for the judgment CLI."""

from __future__ import annotations

import json
from datetime import date

from daily_stock_judgment.domain.bar import Bar
from daily_stock_judgment.domain.ticker import Ticker

INSTRUCTION_BLOCK = """\
あなたは日本株の大引け後日次判断アシスタントです。
与えられた入力 JSON 以外の情報（ニュース・業績・需給の推測など）は使わないでください。
理由には終値まわりの水準か変化（前日比・直近高安との位置など）を1つ以上含めてください。
解釈は短くて構いません。出来高への言及は任意です。
禁止: 入力にない情報の断定、数字も水準もない雰囲気だけの表現、発注を促す言い回し、理由本文でのラベル語（買う／売る／様子見）。
出力は次の JSON オブジェクトのみ（前後に説明文を付けない）。label フィールドは出さない。
{"ticker":"7203.T","score":0,"reason":"..."}
score は整数で -100 から +100。reason はおおよそ200文字以内。
解釈の向きは score の符号に合わせてください。
"""


def build_input_payload(
    *,
    ticker: Ticker,
    as_of: date,
    is_holding: bool,
    bars: tuple[Bar, ...],
) -> dict:
    return {
        "ticker": ticker.value,
        "as_of": as_of.isoformat(),
        "is_holding": is_holding,
        "bars": [
            {
                "date": bar.date.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in bars
        ],
    }


def build_prompt(
    *,
    ticker: Ticker,
    as_of: date,
    is_holding: bool,
    bars: tuple[Bar, ...],
) -> str:
    payload = build_input_payload(
        ticker=ticker, as_of=as_of, is_holding=is_holding, bars=bars
    )
    return (
        INSTRUCTION_BLOCK
        + "\n入力 JSON:\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
