from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from daily_stock_judgment.composition import create_app


def test_web_crud_watchlist_and_holdings(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "app.db"))

    add_watch = client.post(
        "/watchlist", data={"ticker": "9984.T"}, follow_redirects=True
    )
    assert add_watch.status_code == 200
    assert 'value="9984.T"' in add_watch.text

    add_holding = client.post(
        "/holdings",
        data={"ticker": "8035.T", "quantity": "100"},
        follow_redirects=True,
    )
    assert add_holding.status_code == 200
    assert 'value="8035.T"' in add_holding.text
    assert "× 100" in add_holding.text or "× 100.0" in add_holding.text

    remove_watch = client.post(
        "/watchlist/remove",
        data={"ticker": "9984.T"},
        follow_redirects=True,
    )
    assert 'value="9984.T"' not in remove_watch.text

    remove_holding = client.post(
        "/holdings/remove",
        data={"ticker": "8035.T"},
        follow_redirects=True,
    )
    assert 'value="8035.T"' not in remove_holding.text
