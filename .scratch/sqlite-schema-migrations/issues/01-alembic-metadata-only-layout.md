# AlembicをMetaData-onlyで組む公式な構成は何か

Type: research
Status: resolved

## Question

SQLAlchemy ORM で読み書きせず、Alembic 用に `MetaData` / `Table` 定義だけを持ち、`revision --autogenerate` を下書き運用する場合、公式ドキュメント上の推奨構成（`env.py`・`target_metadata`・パッケージ配置・SQLite URL）は何か。このリポジトリ（`sqlite3` ストア継続・`DSJ_DB_PATH`）に落とすときの要点も。

## Answer

公式は ORM を要求せず、`env.py` で Core の `MetaData`（中の `Table`）を `target_metadata` に渡し、`context.configure(..., render_as_batch=True)` する構成。autogenerate は候補のみで必ず人手レビュー。URL は ini 固定ではなく `env.py` で `DSJ_DB_PATH`／既定 `data/app.db` から `sqlite:///` または `sqlite:////` を組み立てる。詳細は [research/alembic-metadata-only-layout.md](../research/alembic-metadata-only-layout.md)。
