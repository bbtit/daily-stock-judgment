from __future__ import annotations

import uvicorn

from daily_stock_judgment.composition import app
from daily_stock_judgment.logging_config import configure_logging


def main() -> None:
    configure_logging()
    # Access lines come from RequestContextMiddleware (JSON + trace_id).
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)


if __name__ == "__main__":
    main()
