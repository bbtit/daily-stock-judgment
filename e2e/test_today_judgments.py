"""今日の判断一覧のブラウザ振る舞い。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_銘柄を登録して判断を実行したとき今日の一覧に結果が出る(
    page: Page, app_url: str
) -> None:
    page.goto(f"{app_url}/")

    add = page.get_by_role("form", name="ウォッチリストに追加")
    add.get_by_label("ウォッチリストのティッカー").fill("7203.T")
    add.get_by_role("button", name="追加").click()

    page.get_by_role("form", name="判断ランを実行").get_by_role(
        "button", name="判断を実行"
    ).click()

    results = page.get_by_role("list", name="今日の判断結果")
    expect(results.get_by_role("listitem")).to_contain_text("7203.T")
    expect(results.get_by_role("listitem")).to_contain_text("スコア")
    expect(results.get_by_role("listitem")).to_contain_text("買う")


def test_判断未実行のとき今日の判断は空状態になる(
    page: Page, app_url: str
) -> None:
    page.goto(f"{app_url}/")
    expect(page.get_by_role("heading", name="今日の判断")).to_be_visible()
    expect(page.get_by_text("まだ今日の判断はありません。")).to_be_visible()
