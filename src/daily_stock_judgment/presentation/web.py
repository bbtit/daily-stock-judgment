from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from urllib.parse import quote

import structlog
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from daily_stock_judgment.application import manage_instruments as uc
from daily_stock_judgment.application.ports import (
    InstrumentBook,
    JudgmentBook,
    JudgmentModel,
    MarketDataSource,
)
from daily_stock_judgment.application.past_judgments import load_past_view
from daily_stock_judgment.application.today_judgments import (
    DayRunStore,
    load_today_view,
    run_today_judgments,
)
from daily_stock_judgment.domain.result import Err
from daily_stock_judgment.presentation.request_context import (
    RequestContextMiddleware,
)

logger = structlog.get_logger(__name__)

_PRESENTATION_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(_PRESENTATION_DIR / "templates"))
_FAVICON = _PRESENTATION_DIR / "static" / "favicon.ico"


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
    app.add_middleware(RequestContextMiddleware)
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

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(_FAVICON, media_type="image/x-icon")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        as_of = app.state.today()
        view = load_today_view(
            as_of=as_of,
            judgments=judgments,
            runs=runs,
            market=app.state.market,
        )
        history_raw = request.query_params.get("history_as_of")
        history_selected: date | None = None
        if history_raw:
            try:
                history_selected = date.fromisoformat(history_raw)
            except ValueError:
                history_selected = None
        past = load_past_view(
            today=as_of,
            selected=history_selected,
            judgments=judgments,
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
                "history_dates": past.available_dates,
                "history_as_of": (
                    past.selected.isoformat() if past.selected else None
                ),
                "history_rows": past.rows,
            },
        )

    @app.post("/judgments/run")
    def run_judgments() -> RedirectResponse:
        as_of = app.state.today()
        logger.info("judgments_run_start", as_of=as_of.isoformat())
        view = run_today_judgments(
            as_of=as_of,
            book=book,
            judgments=judgments,
            runs=runs,
            market=app.state.market,
            model=app.state.model,
        )
        logger.info(
            "judgments_run_finished",
            as_of=view.as_of.isoformat(),
            market_closed=view.market_closed,
            rows=len(view.rows),
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

    @app.post("/holdings")
    def add_holding(
        ticker: str = Form(...),
        quantity: str = Form(""),
        purchase_date: str = Form(""),
        unit_cost: str = Form(""),
    ) -> RedirectResponse:
        raw = quantity.strip()
        if raw == "":
            return _redirect_home("数量を入力してください")
        try:
            qty = int(raw)
        except ValueError:
            return _redirect_home("数量は整数で入力してください")

        raw_date = purchase_date.strip()
        if raw_date == "":
            return _redirect_home("取得日を入力してください")
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError:
            return _redirect_home("取得日は日付で入力してください")

        raw_cost = unit_cost.strip()
        if raw_cost == "":
            return _redirect_home("単価を入力してください")
        try:
            parsed_cost = float(raw_cost)
        except ValueError:
            return _redirect_home("単価は数値で入力してください")

        result = uc.register_holding(
            book,
            ticker,
            quantity=qty,
            purchase_date=parsed_date,
            unit_cost=parsed_cost,
        )
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
