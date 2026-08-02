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
    assert "× 100" in response.text


def test_保有を取得日と単価付きで登録したときレスポンスに表示される(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/holdings",
        data={
            "ticker": "8035.T",
            "quantity": "100",
            "purchase_date": "2026-07-31",
            "unit_cost": "2500",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'value="8035.T"' in response.text
    assert "2500円" in response.text
    assert "2026-07-31 取得" in response.text


def test_保有を不正な単価で登録しようとしたときエラーになる(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/holdings",
        data={"ticker": "8035.T", "quantity": "100", "unit_cost": "abc"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "単価は数値で入力してください" in response.text
    assert 'value="8035.T"' not in response.text


def test_保有を小数の数量で登録しようとしたときエラーになる(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/holdings",
        data={"ticker": "8035.T", "quantity": "100.5"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "数量は整数で入力してください" in response.text
    assert 'value="8035.T"' not in response.text


def test_保有を数量なしで登録しようとしたときエラーになる(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/holdings",
        data={"ticker": "8035.T", "quantity": ""},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "数量を入力してください" in response.text
    assert 'value="8035.T"' not in response.text


def test_保有を数量0で登録しようとしたときエラーになる(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    response = client.post(
        "/holdings",
        data={"ticker": "8035.T", "quantity": "0"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "quantity must be positive" in response.text
    assert 'value="8035.T"' not in response.text


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
