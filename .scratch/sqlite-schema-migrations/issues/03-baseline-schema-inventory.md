# ベースラインに載せる現行スキーマは何か

Type: task
Status: open

## Question

（決定というより棚卸し）現行の SQLite ストアが持つ `CREATE TABLE`（`watchlist` / `holdings` / `judgments` / `day_runs` 等）を洗い出し、baseline revision の候補 DDL として確定する。既存 `data/app.db` の実スキーマとの差分があれば記録する。
