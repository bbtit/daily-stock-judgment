# MetaData定義の置き場所はどこか

Type: grilling
Status: resolved
Blocked by: 01

## Question

Alembic が参照する `MetaData` / テーブル定義を、このリポジトリのどこに置くか。`infrastructure` 配下のモジュール名、ドメイン層との境界、autogenerate が追う単位（1 MetaData に全テーブルか）を決める。

## Answer

`src/daily_stock_judgment/infrastructure/schema.py` に1モジュールで置く。`MetaData` は1つで全テーブルを登録し、autogenerate は DB 全体と一括比較する。`domain` / `application` / `presentation` は import せず、infrastructure 専用（`env.py` と必要なら同層ストアのみ）。版の履歴は `alembic/versions/` 側。
