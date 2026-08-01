from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from daily_stock_judgment.registry import InstrumentRegistry

DEFAULT_DB_PATH = Path(
    os.environ.get(
        "DSJ_DB_PATH",
        Path.home() / ".local" / "share" / "daily-stock-judgment" / "app.db",
    )
)

TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


def create_app(db_path: Path | None = None) -> FastAPI:
    registry = InstrumentRegistry(db_path or DEFAULT_DB_PATH)
    app = FastAPI(title="日次売買判断")
    app.state.registry = registry

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "watchlist": registry.list_watchlist(),
                "holdings": registry.list_holdings(),
            },
        )

    @app.post("/watchlist")
    def add_watchlist(ticker: str = Form(...)) -> RedirectResponse:
        registry.add_to_watchlist(ticker)
        return RedirectResponse("/", status_code=303)

    @app.post("/watchlist/remove")
    def remove_watchlist(ticker: str = Form(...)) -> RedirectResponse:
        registry.remove_from_watchlist(ticker)
        return RedirectResponse("/", status_code=303)

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
            qty = float(raw)
        registry.register_holding(ticker, quantity=qty)
        return RedirectResponse("/", status_code=303)

    @app.post("/holdings/remove")
    def remove_holding(ticker: str = Form(...)) -> RedirectResponse:
        registry.unregister_holding(ticker)
        return RedirectResponse("/", status_code=303)

    return app


app = create_app()
