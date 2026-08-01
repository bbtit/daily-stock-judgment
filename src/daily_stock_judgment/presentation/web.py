from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from daily_stock_judgment.application import manage_instruments as uc
from daily_stock_judgment.application.ports import (
    InstrumentBook,
    JudgmentBook,
    JudgmentModel,
    MarketDataSource,
)
from daily_stock_judgment.application.today_judgments import (
    DayRunStore,
    load_today_view,
    run_today_judgments,
)
from daily_stock_judgment.domain.result import Err

TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


def create_app(
    book: InstrumentBook,
    *,
    judgments: JudgmentBook,
    runs: DayRunStore,
    market: MarketDataSource,
    model: JudgmentModel,
    today: Callable[[], date],
) -> FastAPI:
    app = FastAPI(title="日次売買判断")
    app.state.book = book
    app.state.judgments = judgments
    app.state.runs = runs
    app.state.market = market
    app.state.model = model
    app.state.today = today

    def _redirect_home(error: str | None = None) -> RedirectResponse:
        if error:
            return RedirectResponse(f"/?error={quote(error)}", status_code=303)
        return RedirectResponse("/", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        as_of = app.state.today()
        view = load_today_view(
            as_of=as_of,
            judgments=judgments,
            runs=runs,
            market=app.state.market,
        )
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "watchlist": uc.list_watchlist(book),
                "holdings": uc.list_holdings(book),
                "error": request.query_params.get("error"),
                "as_of": view.as_of.isoformat(),
                "market_closed": view.market_closed,
                "judgment_rows": view.rows,
            },
        )

    @app.post("/judgments/run")
    def run_judgments() -> RedirectResponse:
        run_today_judgments(
            as_of=app.state.today(),
            book=book,
            judgments=judgments,
            runs=runs,
            market=app.state.market,
            model=app.state.model,
        )
        return _redirect_home()

    @app.post("/watchlist")
    def add_watchlist(ticker: str = Form(...)) -> RedirectResponse:
        result = uc.add_to_watchlist(book, ticker)
        if isinstance(result, Err):
            return _redirect_home(result.error)
        return _redirect_home()

    @app.post("/watchlist/remove")
    def remove_watchlist(ticker: str = Form(...)) -> RedirectResponse:
        result = uc.remove_from_watchlist(book, ticker)
        if isinstance(result, Err):
            return _redirect_home(result.error)
        return _redirect_home()

    @app.post("/watchlist/replace")
    def replace_watchlist(
        old_ticker: str = Form(...),
        new_ticker: str = Form(...),
    ) -> RedirectResponse:
        result = uc.replace_watchlist_ticker(book, old_ticker, new_ticker)
        if isinstance(result, Err):
            return _redirect_home(result.error)
        return _redirect_home()

    @app.post("/holdings")
    def add_holding(
        ticker: str = Form(...),
        quantity: str = Form(""),
    ) -> RedirectResponse:
        raw = quantity.strip()
        qty: float | None
        if raw == "":
            qty = None
        else:
            try:
                qty = float(raw)
            except ValueError:
                return _redirect_home("数量は数値で入力してください")
        result = uc.register_holding(book, ticker, quantity=qty)
        if isinstance(result, Err):
            return _redirect_home(result.error)
        return _redirect_home()

    @app.post("/holdings/remove")
    def remove_holding(ticker: str = Form(...)) -> RedirectResponse:
        result = uc.unregister_holding(book, ticker)
        if isinstance(result, Err):
            return _redirect_home(result.error)
        return _redirect_home()

    return app
