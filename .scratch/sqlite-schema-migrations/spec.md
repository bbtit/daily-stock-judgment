# SQLite スキーマ移行（Alembic）

Status: ready-for-agent

## Problem Statement

アプリの SQLite スキーマは各ストアが起動時に `CREATE TABLE IF NOT EXISTS` で自行初期化しており、変更履歴もロールバック手段もない。テーブルや列を変えるたびに手作業とデータ破損のリスクが増え、既存の `data/app.db`（判断・ウォッチリスト・保有などの正本）を壊さずに進化させられない。

## Solution

Alembic でスキーマ変更を版管理する。起動時に未適用分を自動適用し、失敗したらアプリを上げない。人が戻すときは Alembic CLI で downgrade する。既存 DB はデータを残したまま初回だけ stamp で取り込む。読み書きはこれまでどおり sqlite3 ストアのままにし、SQLAlchemy はスキーマ定義（MetaData）とマイグレーション実行にだけ使う。

## User Stories

1. As a developer, I want schema changes recorded as ordered revisions, so that I know what ran against a given database.
2. As a developer, I want a single current-schema definition (MetaData) for autogenerate, so that draft revisions compare against one source of truth.
3. As a developer, I want autogenerate output treated as a draft, so that I can correct renames and data moves before committing.
4. As a developer, I want each revision to include both upgrade and downgrade steps, so that I can move the database forward and back from the CLI.
5. As an operator of my personal app, I want the app to apply pending upgrades on startup, so that I do not forget to migrate before using the UI.
6. As an operator, I want startup to fail closed if upgrade fails, so that I never run against a half-migrated schema.
7. As an operator, I want downgrade available only via CLI, so that I cannot accidentally roll back from the UI.
8. As an operator, I want to use stock `uv run alembic …` without a custom wrapper, so that I learn the standard tool surface.
9. As an operator, I want Alembic to honor `DSJ_DB_PATH` (and the default project `data/app.db`), so that CLI and app touch the same file.
10. As a developer, I want schema ownership to live only in Alembic revisions, so that stores stop embedding DDL.
11. As a developer, I want domain and application layers free of SQLAlchemy/schema imports, so that layer boundaries stay clean.
12. As a developer, I want one MetaData registering all app tables, so that autogenerate compares the whole app database at once.
13. As a developer, I want a baseline revision that matches today’s four tables (watchlist, holdings, judgments, day_runs), so that new databases and stamped legacy DBs share the same starting point.
14. As an operator with an existing `app.db`, I want a stamp procedure that preserves my rows, so that I do not lose judgments or instrument data.
15. As an operator, I want to drop the orphan hand-rolled `schema_migrations` table before stamp, so that only Alembic’s version table tracks migrations going forward.
16. As an operator, I want to visually verify `.schema` against the baseline inventory before stamp, so that I do not stamp a mismatched database.
17. As an operator, I want stamp aborted on mismatch, so that I fix baseline, MetaData, or the DB before continuing.
18. As a developer, I want SQLite batch mode enabled for autogenerate, so that column changes are expressed in a form SQLite can apply.
19. As a developer, I want composition to run upgrade after resolving the DB path and before constructing stores, so that every store opens an already-migrated database.
20. As a developer writing tests, I want a focused migration smoke test via `create_app` on a temporary empty DB, so that I know migrate-then-use works.
21. As a developer, I want that smoke test to assert the four tables exist and that stores can do light read/write, so that “app works after migrate” is concrete.
22. As a developer, I do not want automated downgrade round-trips as a gate, so that test cost stays tied to the real startup path.
23. As a developer, I want existing SQLite/HTTP tests that use `create_app` to keep working once DDL moves to migrations, so that the suite remains the safety net for app behavior.
24. As a developer, I want revision history to live under the Alembic versions directory, so that MetaData always describes head and history stays in revisions.
25. As a future developer adding a column, I want a documented happy path (edit MetaData → autogenerate → review → upgrade on next start), so that day-to-day changes are routine.
26. As an operator, I want stamp to be a one-time onboarding step, so that later changes use only upgrade/downgrade.
27. As a developer, I want SQLAlchemy limited to MetaData/migrations, so that we do not rewrite store CRUD in this effort.
28. As a reader of architecture docs, I want persistence guidance updated to describe Alembic as schema authority, so that future work does not reintroduce store DDL.

## Implementation Decisions

- Use Alembic + SQLAlchemy as the migration stack (Python de facto). Application CRUD remains on the sqlite3-backed stores.
- Place a single Core `MetaData` with all application tables in an infrastructure schema module. Only infrastructure and Alembic `env.py` import it; domain, application, and presentation do not.
- Autogenerate targets that one MetaData. Treat generated revisions as drafts; always human-review before commit (especially renames and data moves).
- Configure Alembic `env.py` with `render_as_batch=True` for SQLite. Resolve the database URL from `DSJ_DB_PATH` or the project default `data/app.db` (same rules as composition).
- Schema authority is Alembic revisions only. Remove `CREATE TABLE IF NOT EXISTS` (and equivalent) from SQLite stores; stores assume tables already exist after upgrade.
- Baseline revision creates exactly: watchlist, holdings, judgments, day_runs — matching the inventory (no secondary indexes; holdings.quantity nullable; judgments composite PK; day_runs boolean-ish INTEGER + JSON text).
- On app startup, after DB path preparation and before store construction, run `upgrade` to head. On failure, raise and do not serve the app.
- Human CLI is stock Alembic via the package runner (e.g. `uv run alembic …`). No project-specific migrate wrapper. Downgrade, stamp, and revision creation are CLI-only.
- Existing live DB adoption (one-time): visually diff `.schema` to baseline inventory → `DROP` orphan `schema_migrations` if present → `alembic stamp head` when schemas match. On mismatch, do not stamp; stop and fix. Do not delete application row data as part of stamp.
- Alembic’s own version table is the ledger going forward; the discarded hand-rolled `schema_migrations` table is not part of the baseline target schema.
- Keep fog deferred (not blocking this spec): how to author data-moving revisions, multiple-head merge policy, offline SQL generation need.

## Testing Decisions

- Good tests assert external behavior after migration: the app composition path leaves a usable schema and stores can persist domain values. Do not assert Alembic internals, revision file text, or downgrade round-trips in CI.
- Primary seam: composition `create_app` (path resolve → upgrade → stores). One focused module/file for migration smoke covers empty temporary DB → `create_app` → four tables present → light read/write through the SQLite stores.
- Prefer this highest seam over calling Alembic APIs directly in tests, unless a future failure cannot be observed through `create_app`.
- Prior art: existing `tests/` SQLite store tests and Web `TestClient` tests that already construct apps with a temporary DB path; HTTP tests using `create_app` become indirect regression coverage once startup always migrates.
- Automated downgrade tests are out of the required suite; CLI downgrade remains a manual capability.
- Follow repo testing style: Japanese behavior-oriented test names where possible; `uv run pytest` includes the migration smoke test with the rest of `tests/`.

## Out of Scope

- Migrating store read/write from sqlite3 to SQLAlchemy ORM/Core
- Changing database engine (e.g. PostgreSQL)
- Multi-process / zero-downtime migration
- Migration management UI or HTTP endpoints for upgrade/downgrade
- Product features unrelated to persistence (judgment UX, market adapters, etc.)
- Deciding data-migration revision conventions, multiple-head merges, or offline SQL generation in this delivery (left as map fog)

## Further Notes

- Wayfinder map: `.scratch/sqlite-schema-migrations/map.md` — all charted tickets resolved; remaining fog intentionally not ticketed for first delivery.
- Research assets: Alembic MetaData-only layout notes; baseline schema inventory (four tables + orphan `schema_migrations` on live DB).
- After implementation, update architecture persistence section so schema authority is documented outside the wayfinder map.
- First live onboarding of `data/app.db` is an operator checklist (verify → drop orphan → stamp), not an automatic silent stamp on every start.
