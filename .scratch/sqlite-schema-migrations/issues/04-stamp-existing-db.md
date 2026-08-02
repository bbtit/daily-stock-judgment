# 既存app.dbのstamp手順と一致確認はどうするか

Type: grilling
Status: open
Blocked by: 01, 03

## Question

既にテーブルがある `data/app.db` を、データを残したまま Alembic 管理下に載せる具体手順は何か。`stamp` のタイミング、「スキーマ一致」の確認方法（目視 / `check` / 差分コマンド）、一致しない場合の扱いを決める。
