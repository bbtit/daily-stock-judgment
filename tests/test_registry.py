from __future__ import annotations

from pathlib import Path

from daily_stock_judgment.registry import InstrumentRegistry


def test_add_and_list_watchlist(tmp_path: Path) -> None:
    registry = InstrumentRegistry(tmp_path / "app.db")

    registry.add_to_watchlist("7203.T")

    assert registry.list_watchlist() == ["7203.T"]


def test_remove_from_watchlist(tmp_path: Path) -> None:
    registry = InstrumentRegistry(tmp_path / "app.db")
    registry.add_to_watchlist("7203.T")
    registry.add_to_watchlist("6758.T")

    registry.remove_from_watchlist("7203.T")

    assert registry.list_watchlist() == ["6758.T"]


def test_register_holding_with_optional_quantity(tmp_path: Path) -> None:
    registry = InstrumentRegistry(tmp_path / "app.db")

    registry.register_holding("7203.T", quantity=100)
    registry.register_holding("6758.T")

    assert registry.list_holdings() == [
        {"ticker": "6758.T", "quantity": None},
        {"ticker": "7203.T", "quantity": 100.0},
    ]


def test_unregister_holding(tmp_path: Path) -> None:
    registry = InstrumentRegistry(tmp_path / "app.db")
    registry.register_holding("7203.T", quantity=10)

    registry.unregister_holding("7203.T")

    assert registry.list_holdings() == []


def test_update_holding_quantity(tmp_path: Path) -> None:
    registry = InstrumentRegistry(tmp_path / "app.db")
    registry.register_holding("7203.T", quantity=10)

    registry.register_holding("7203.T", quantity=20)

    assert registry.list_holdings() == [{"ticker": "7203.T", "quantity": 20.0}]


def test_persists_across_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    first = InstrumentRegistry(db_path)
    first.add_to_watchlist("7203.T")
    first.register_holding("6758.T", quantity=5)

    second = InstrumentRegistry(db_path)

    assert second.list_watchlist() == ["7203.T"]
    assert second.list_holdings() == [{"ticker": "6758.T", "quantity": 5.0}]
