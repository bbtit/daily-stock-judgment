# AGENTS.md

## Cursor Cloud specific instructions

This is a single Python product: **日次売買判断 (Daily Stock Judgment)** — a localhost FastAPI web app for post-close daily judgments on Japanese equities. Managed with `uv` (Python 3.13, pinned in `.python-version`). Standard setup/run/test commands live in `README.md`; only non-obvious caveats are noted here.

### Environment / startup caveats

- `uv` installs to `~/.local/bin`. If `uv` is not on `PATH` in a fresh shell, add it: `export PATH="$HOME/.local/bin:$PATH"`. The startup update script (`uv sync`) already provisions Python 3.13 and the venv.
- Run everything through `uv run ...` so the project venv is used (do not rely on the system `python`, which is 3.12).
- The single long-running service is the web app. Start it (dev) and it will auto-create + Alembic-migrate the SQLite DB (`data/app.db`, override with `DSJ_DB_PATH`) on startup — no separate DB/migration step needed:
  - `uv run daily-stock-judgment` → serves http://127.0.0.1:8000
- Prefer demo mode for any offline / cloud testing so no network (Yahoo Finance) or external LLM CLI is required. Demo adapters are deterministic:
  - `DSJ_MARKET=demo DSJ_JUDGMENT_MODEL=demo uv run daily-stock-judgment`
  - Optionally pin the judgment date with `DSJ_AS_OF=YYYY-MM-DD`.
- Real mode needs network (`yfinance`) and a local agent CLI via `DSJ_AGENT_CLI` (e.g. `agent -p {prompt} --trust`); without `--trust`/equivalent the agent returns no JSON and results show "判断失敗". This is not available in the cloud VM by default.

### Testing caveats

- Unit/integration tests (`uv run pytest -q`) use in-memory fakes / demo adapters — no network or Playwright needed.
- E2E tests (`uv run pytest e2e -q`) require Playwright Chromium (`uv run playwright install chromium`). The E2E fixture spawns its own app subprocess in demo mode on a random port, so you do NOT need the app already running. To instead target a running instance: `BASE_URL=http://127.0.0.1:8000 uv run pytest e2e -q`.
- There is no lint/format/typecheck tooling configured in this repo, and no CI/Docker/Makefile.
