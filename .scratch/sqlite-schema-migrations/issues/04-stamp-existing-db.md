# 既存app.dbのstamp手順と一致確認はどうするか

Type: grilling
Status: resolved
Blocked by: 01, 03

## Question

既にテーブルがある `data/app.db` を、データを残したまま Alembic 管理下に載せる具体手順は何か。`stamp` のタイミング、「スキーマ一致」の確認方法（目視 / `check` / 差分コマンド）、一致しない場合の扱いを決める。

前提（[ベースラインに載せる現行スキーマは何か](03-baseline-schema-inventory.md)）: 4テーブルはコードと一致。ライブ DB のみに孤児 `schema_migrations`（破棄済み手書き migrate の名残）がある — stamp 時に DROP するか放置するかも含めて決める。

## Answer

初回取り込み: baseline 用意後に `.schema` を inventory と目視突合 → 孤児 `schema_migrations` を `DROP` → `alembic stamp head`（行データは触らない）。不一致なら stamp せず停止し、baseline / `schema.py` / DB のどれが正かを直してからやり直す。stamp は初回のみ；以降は通常の upgrade/downgrade。
