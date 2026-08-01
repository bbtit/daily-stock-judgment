"""ウォッチリスト / 保有のブラウザ振る舞い。

セレクタは role とアクセシブル名のみ。FastAPI/Jinja の内部構造には依存しない。
将来 FE/BE を分離しても、BASE_URL を差し替えれば同じスイートを使える。
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_銘柄が未登録のときホームに空状態が表示される(
    page: Page, app_url: str
) -> None:
    page.goto(f"{app_url}/")
    expect(page.get_by_role("heading", name="日次売買判断")).to_be_visible()
    expect(page.get_by_role("heading", name="ウォッチリスト")).to_be_visible()
    expect(page.get_by_role("heading", name="保有")).to_be_visible()
    expect(page.get_by_text("まだ銘柄がありません。")).to_be_visible()
    expect(page.get_by_text("保有はありません。")).to_be_visible()


def test_ウォッチリストにティッカーを追加したとき一覧に表示される(
    page: Page, app_url: str
) -> None:
    page.goto(f"{app_url}/")

    add = page.get_by_role("form", name="ウォッチリストに追加")
    add.get_by_label("ウォッチリストのティッカー").fill("7203.T")
    add.get_by_role("button", name="追加").click()

    watchlist = page.get_by_role("list", name="ウォッチリストの銘柄")
    expect(watchlist).to_contain_text("7203.T")


def test_ウォッチリストから削除したとき空状態に戻る(
    page: Page, app_url: str
) -> None:
    page.goto(f"{app_url}/")

    add = page.get_by_role("form", name="ウォッチリストに追加")
    add.get_by_label("ウォッチリストのティッカー").fill("7203.T")
    add.get_by_role("button", name="追加").click()

    page.get_by_role("form", name="ウォッチリストから削除").get_by_role(
        "button", name="削除"
    ).click()
    expect(page.get_by_text("まだ銘柄がありません。")).to_be_visible()


def test_保有を数量付きで登録したとき一覧にティッカーと数量が表示される(
    page: Page, app_url: str
) -> None:
    page.goto(f"{app_url}/")

    form = page.get_by_role("form", name="保有を登録")
    form.get_by_label("保有のティッカー").fill("8035.T")
    form.get_by_label("保有数量").fill("100")
    form.get_by_role("button", name="登録 / 更新").click()

    holdings = page.get_by_role("list", name="保有銘柄")
    expect(holdings).to_contain_text("8035.T")
    expect(holdings).to_contain_text("100")


def test_保有を解除したとき空状態に戻る(page: Page, app_url: str) -> None:
    page.goto(f"{app_url}/")

    form = page.get_by_role("form", name="保有を登録")
    form.get_by_label("保有のティッカー").fill("8035.T")
    form.get_by_label("保有数量").fill("100")
    form.get_by_role("button", name="登録 / 更新").click()

    page.get_by_role("form", name="保有を解除").get_by_role(
        "button", name="解除"
    ).click()
    expect(page.get_by_text("保有はありません。")).to_be_visible()


def test_不正なティッカーを追加しようとしたときエラーが表示され一覧は空のまま(
    page: Page, app_url: str
) -> None:
    page.goto(f"{app_url}/")

    add = page.get_by_role("form", name="ウォッチリストに追加")
    add.get_by_label("ウォッチリストのティッカー").fill("not-a-ticker")
    add.get_by_role("button", name="追加").click()

    alert = page.get_by_role("alert")
    expect(alert).to_be_visible()
    expect(alert).not_to_be_empty()
    expect(page.get_by_text("まだ銘柄がありません。")).to_be_visible()
