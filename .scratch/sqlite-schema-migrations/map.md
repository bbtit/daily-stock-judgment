# SQLiteスキーマ移行の運用

## Destination

SQLite スキーマ変更の運用が決まっていること。Alembic を前提に、追加の仕方・適用タイミング・既存 DB・失敗時・up/down・テスト方針まで合意し、この地図の Decisions so far が揃って道が晴れたら完了。`ARCHITECTURE` への反映や実装は別作業。

## Notes

- ドメイン: 日次株価売買判断ツール。用語はリポジトリ根の `CONTEXT.md` を正とする。永続化はローカル SQLite（`data/app.db` / `DSJ_DB_PATH`）。レイヤ境界は `docs/ARCHITECTURE.md`。
- 毎セッション参照: `/grilling`, `/domain-modeling`, 必要なら `/research`。実装フェーズに入ったら `/tdd`。
- 立ち位置の好み（チャート時）:
  - 仕組みは **Alembic + SQLAlchemy**（Python デファクト）。
  - 起動時に未適用分を **自動 `upgrade`**。失敗したら **起動中止**。
  - **up / down 両方**。`downgrade` は **CLI のみ**（UI なし）。
  - 新規 revision は **autogenerate を下書き**にし、人間が確認・修正してからコミット。
  - スキーマの正本は **Alembic revision のみ**。ストアの `CREATE TABLE IF NOT EXISTS` は外す。
  - 既存 DB はデータ維持で **baseline + stamp**。
  - SQLAlchemy は **MetaData / テーブル定義のみ**。読み書きは当面 `sqlite3` のまま。
  - **upgrade↔downgrade 往復**を自動テストする。
- このマップは計画まで。文書化・実装は道が晴れてから別作業。
- Issue tracker: local markdown（`.scratch/`）。

## Decisions so far

<!-- the index — one line per closed ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [AlembicをMetaData-onlyで組む公式な構成は何か](.scratch/sqlite-schema-migrations/issues/01-alembic-metadata-only-layout.md) — Core MetaData を env.py の target_metadata に渡し、SQLite は render_as_batch=True、URL は DSJ_DB_PATH から組み立て、autogenerate は人手レビュー必須

## Not yet specified

- データ移行を含む revision（列追加以上）の書き方・レビュー観点
- 複数 head ができたときの merge 方針
- offline SQL 生成（`alembic upgrade --sql`）の要否

## Out of scope

- ストア読み書きの SQLAlchemy / ORM 移行（MetaData のみが境界）
- PostgreSQL 等への DB エンジン変更
- 複数プロセス／ゼロダウンタイム移行
- マイグレーション管理 UI
