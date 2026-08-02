# Baseline schema inventory

Date: 2026-08-02  
Sources: store `_init_schema` DDL + `data/app.db` `.schema`

## Baseline candidate (from code — authoritative for Alembic baseline)

Four tables. No secondary indexes. Source: `sqlite_instrument_store.py`, `sqlite_judgment_store.py`, `sqlite_day_run_store.py`.

```sql
CREATE TABLE watchlist (
    ticker TEXT PRIMARY KEY COLLATE NOCASE
);

CREATE TABLE holdings (
    ticker TEXT PRIMARY KEY COLLATE NOCASE,
    quantity REAL
);

CREATE TABLE judgments (
    ticker TEXT NOT NULL COLLATE NOCASE,
    as_of TEXT NOT NULL,
    score INTEGER NOT NULL,
    label TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY (ticker, as_of)
);

CREATE TABLE day_runs (
    as_of TEXT PRIMARY KEY,
    market_closed INTEGER NOT NULL,
    outcomes_json TEXT NOT NULL
);
```

Notes:

- `holdings.quantity` is nullable (`REAL` without `NOT NULL`) — matches code.
- `judgments` composite PK `(ticker, as_of)`; ticker/as_of use `COLLATE NOCASE` on ticker only.
- `day_runs.market_closed` is INTEGER (boolean-ish); `outcomes_json` is TEXT.

## `data/app.db` live schema

| Table | In code? | Match code DDL? | Rows (2026-08-02) |
| --- | --- | --- | --- |
| `watchlist` | yes | yes (whitespace only) | 1 |
| `holdings` | yes | yes (whitespace only) | 1 |
| `judgments` | yes | yes (whitespace only) | 2 |
| `day_runs` | yes | yes (whitespace only) | 2 |
| `schema_migrations` | **no** | n/a | 1 row (`001_baseline`) |

### Diff vs code

- **Only material diff:** live DB has orphan `schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)` from a discarded hand-rolled migrate WIP. Not part of store DDL; **not** part of Alembic baseline target.
- Alembic will track versions in its own `alembic_version` table — do not treat `schema_migrations` as the migration ledger going forward.
- Stamp / adopt path (ticket 04) should decide: drop the orphan table, or leave it unused.

## Out of baseline

- `data/lhci.db` — Lighthouse CI, unrelated.
- No views, triggers, or FTS tables in `app.db`.
