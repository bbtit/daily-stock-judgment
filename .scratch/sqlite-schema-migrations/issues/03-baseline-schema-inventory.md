# ベースラインに載せる現行スキーマは何か

Type: task
Status: resolved

## Question

（決定というより棚卸し）現行の SQLite ストアが持つ `CREATE TABLE`（`watchlist` / `holdings` / `judgments` / `day_runs` 等）を洗い出し、baseline revision の候補 DDL として確定する。既存 `data/app.db` の実スキーマとの差分があれば記録する。

## Answer

ベースライン候補はコード上の4テーブル — `watchlist` / `holdings` / `judgments` / `day_runs`（二次インデックスなし）。`data/app.db` の同名テーブルは DDL 一致（空白差のみ）。差分は破棄済み手書き migrate の名残である **`schema_migrations` だけ**（baseline 対象外。stamp 時に破棄 or 放置を決める）。詳細: [research/baseline-schema-inventory.md](../research/baseline-schema-inventory.md)。
