from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from daily_stock_judgment.composition import create_app


def test_favicon_icoを返す(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert response.content[:4] == b"\x00\x00\x01\x00"


def test_ウォッチリストに追加したときレスポンスにティッカーが含まれる(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/watchlist", data={"ticker": "9984.T"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert 'value="9984.T"' in response.text


def test_ウォッチリストから削除したときレスポンスからティッカーが消える(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))
    client.post("/watchlist", data={"ticker": "9984.T"}, follow_redirects=True)

    response = client.post(
        "/watchlist/remove",
        data={"ticker": "9984.T"},
        follow_redirects=True,
    )

    assert 'value="9984.T"' not in response.text


def test_保有を数量付きで登録したときレスポンスにティッカーと数量が含まれる(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/holdings",
        data={"ticker": "8035.T", "quantity": "100"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'value="8035.T"' in response.text
    assert "× 100" in response.text or "× 100.0" in response.text


def test_保有を解除したときレスポンスからティッカーが消える(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))
    client.post(
        "/holdings",
        data={"ticker": "8035.T", "quantity": "100"},
        follow_redirects=True,
    )

    response = client.post(
        "/holdings/remove",
        data={"ticker": "8035.T"},
        follow_redirects=True,
    )

    assert 'value="8035.T"' not in response.text
