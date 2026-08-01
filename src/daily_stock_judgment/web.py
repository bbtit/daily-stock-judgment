from __future__ import annotations

import os
import shutil
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from daily_stock_judgment.registry import InstrumentRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DB_PATH = (
    Path.home() / ".local" / "share" / "daily-stock-judgment" / "app.db"
)
DEFAULT_DB_PATH = (
    Path(os.environ["DSJ_DB_PATH"])
    if "DSJ_DB_PATH" in os.environ
    else PROJECT_ROOT / "data" / "app.db"
)

TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


def _prepare_db_path(db_path: Path) -> Path:
    """Prefer project-local DB; migrate once from the legacy home path."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if (
        db_path == DEFAULT_DB_PATH
        and "DSJ_DB_PATH" not in os.environ
        and not db_path.exists()
        and LEGACY_DB_PATH.exists()
    ):
        shutil.move(str(LEGACY_DB_PATH), str(db_path))
    return db_path


def create_app(db_path: Path | None = None) -> FastAPI:
    resolved = _prepare_db_path(db_path or DEFAULT_DB_PATH)
    registry = InstrumentRegistry(resolved)
    app = FastAPI(title="日次売買判断")
    app.state.registry = registry

    def _redirect_home(error: str | None = None) -> RedirectResponse:
        if error:
            return RedirectResponse(f"/?error={quote(error)}", status_code=303)
        return RedirectResponse("/", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "watchlist": registry.list_watchlist(),
                "holdings": registry.list_holdings(),
                "error": request.query_params.get("error"),
            },
        )

    @app.post("/watchlist")
    def add_watchlist(ticker: str = Form(...)) -> RedirectResponse:
        try:
            registry.add_to_watchlist(ticker)
        except ValueError as exc:
            return _redirect_home(str(exc))
        return _redirect_home()

    @app.post("/watchlist/remove")
    def remove_watchlist(ticker: str = Form(...)) -> RedirectResponse:
        try:
            registry.remove_from_watchlist(ticker)
        except ValueError as exc:
            return _redirect_home(str(exc))
        return _redirect_home()

    @app.post("/watchlist/replace")
    def replace_watchlist(
        old_ticker: str = Form(...),
        new_ticker: str = Form(...),
    ) -> RedirectResponse:
        try:
            registry.replace_watchlist_ticker(old_ticker, new_ticker)
        except ValueError as exc:
            return _redirect_home(str(exc))
        return _redirect_home()

    @app.post("/holdings")
    def add_holding(
        ticker: str = Form(...),
        quantity: str = Form(""),
    ) -> RedirectResponse:
        qty: float | None
        raw = quantity.strip()
        if raw == "":
            qty = None
        else:
            try:
                qty = float(raw)
            except ValueError:
                return _redirect_home("数量は数値で入力してください")
        try:
            registry.register_holding(ticker, quantity=qty)
        except ValueError as exc:
            return _redirect_home(str(exc))
        return _redirect_home()

    @app.post("/holdings/remove")
    def remove_holding(ticker: str = Form(...)) -> RedirectResponse:
        try:
            registry.unregister_holding(ticker)
        except ValueError as exc:
            return _redirect_home(str(exc))
        return _redirect_home()

    return app


app = create_app()
