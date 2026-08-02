# Alembic MetaData-only 構成（公式ドキュメント）

Date: 2026-08-02  
Sources: SQLAlchemy / Alembic official docs only  
Question: ORM 読み書きなしで `MetaData` / `Table` だけを持ち、`revision --autogenerate` を下書き運用する場合の公式推奨構成は何か。本リポジトリ（`sqlite3` 継続・`DSJ_DB_PATH`・既定 `data/app.db`）への落とし所は何か。

## Verdict

公式は **ORM 必須ではない**。`target_metadata` は `sqlalchemy.schema.MetaData`（またはその列）を受け取り、中の `Table` と DB を比較する。ORM Declarative の `Base.metadata` は「MetaData を渡す一例」にすぎない。Core の `MetaData` + `Table` 定義をアプリから import し、`env.py` で `context.configure(..., target_metadata=..., render_as_batch=True)` する構成が、SQLite + MetaData-only + autogenerate 下書きの公式どおりの形。URL は `env.py` で `DSJ_DB_PATH`（未設定時はプロジェクト根の `data/app.db`）から `sqlite:///` / `sqlite:////` を組み立てるのが公式の推奨カスタマイズ経路。

## Findings

### 1. Alembic が要求するのは MetaData であって ORM ではない

- Autogenerate は「アプリ側の table metadata」と「`sqlalchemy.url` が指す DB の現スキーマ」を比較して候補 revision を書く。[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- チュートリアル例は `from myapp.mymodel import Base` / `target_metadata = Base.metadata` だが、本文は「declarative base が持つ MetaData に Table が入っている」前提であり、ORM 操作を要求していない。[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- API: `EnvironmentContext.configure(target_metadata=...)` の型は `MetaData | Sequence[MetaData] | None`。説明は「`sqlalchemy.schema.MetaData` object, or a sequence of MetaData objects」。[runtime](https://alembic.sqlalchemy.org/en/latest/api/runtime.html)
- SQLAlchemy Core では ORM なしで `MetaData` と `Table(..., metadata, Column(...))` を定義するのが正規のスキーマ記述。[Describing Databases with MetaData](https://docs.sqlalchemy.org/en/20/core/metadata.html) / [Working with Database Metadata](https://docs.sqlalchemy.org/en/20/tutorial/metadata.html)

**含意（本リポジトリ）:** 読み書きは `sqlite3` のままにしてよい。Alembic 用に Core `MetaData`/`Table` だけ置けば公式契約を満たす。

### 2. `env.py` と `target_metadata` の配線

- `alembic init` の generic テンプレートが作る `env.py` 先頭付近に `target_metadata = None` があり、アプリの MetaData に差し替える。[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- `run_migrations_online()` で `engine_from_config` → `connection` → `context.configure(connection=..., target_metadata=target_metadata)` → `run_migrations()`。[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- `env.py` はマイグレーション実行のたびに走るカスタムスクリプト。接続方法・アプリライブラリ／モデルのロードはここで好きに変えてよい。[Tutorial — env.py](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- Alembic はアプリと同じ Python path に入っているのが通常望ましい（`env.py` からアプリの metadata を import するため）。[Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

最小パターン（公式の差し替え形 + Core）:

```python
# env.py（概念）
from myapp.schema import metadata  # MetaData; Tables already registered
target_metadata = metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite: see §4
        )
        with context.begin_transaction():
            context.run_migrations()
```

### 3. パッケージ配置（公式が言う範囲）

- マイグレーション環境の標準形: プロジェクト内に `alembic/`（名前は任意）+ ルートの `alembic.ini`、中に `env.py`・`script.py.mako`・`versions/`。[Tutorial — Migration Environment](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- アプリの metadata モジュールは「`env.py` から import できること」が要件。パス配置の細かい規約は公式に固定されていない（本マップの issue `02-metadata-placement` の領域）。
- `versions/` の各 revision がスキーマ変更の正本として残る運用は、プロジェクト Notes（revision のみを正本）と整合。autogenerate は候補をそこに書くだけ。[Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) / [autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)

### 4. SQLite: URL と `render_as_batch`

**URL（SQLAlchemy）**

- 相対: `sqlite:///path/to/database.db`（第 3 スラッシュの右がファイル名）。
- 絶対: `sqlite:////path/to/database.db`（スラッシュ 4 本）。
- 既定 DBAPI は pysqlite（`sqlite3`）。[SQLite dialect — Connect Strings](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#connect-strings) / [Engine — SQLite](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlite)

**バッチ（Alembic）**

- SQLite はほぼ ALTER 非対応のため、列変更などは table recreate（batch）が必要。[batch](https://alembic.sqlalchemy.org/en/latest/batch.html)
- autogenerate が `op.batch_alter_table` を出すには `env.py` で `render_as_batch=True`。[batch — Batch mode with Autogenerate](https://alembic.sqlalchemy.org/en/latest/batch.html)

### 5. 接続 URL を環境変数から取る（公式の明示推奨）

- `alembic.ini` の `sqlalchemy.url` は **`env.py` が読むときだけ**使われる。URL を環境変数やレジストリから取るなら **`env.py` を書き換えよ**、と Tutorial が明記。[Tutorial — sqlalchemy.url](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- `env.py` が ini 以外から接続・ログを取るなら、`alembic.ini` 自体を省略することも可能。[Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

**本リポジトリへの写像**

| アプリ現状 | Alembic 側 |
| --- | --- |
| `DSJ_DB_PATH` があればその Path、なければ `PROJECT_ROOT / "data" / "app.db"`（`composition.py` / ARCHITECTURE） | `env.py` で同じ解決をし、絶対 Path なら `sqlite:////` + path、相対なら作業ディレクトリ基準の `sqlite:///` を `config.set_main_option("sqlalchemy.url", ...)` するか `create_engine` に直接渡す |
| 読み書きは `sqlite3` | Alembic 実行時だけ SQLAlchemy Engine/Connection。アプリの CRUD を ORM 化しない |

### 6. autogenerate は必ず人手レビュー（下書き）

- 「candidate migrations」を生成し、「We review and modify these by hand as needed」。[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- 「autogenerate is not intended to be perfect. It is **always necessary** to manually review and correct」。[autogenerate — What does Autogenerate Detect](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- 生成スクリプトには `### commands auto generated by Alembic - please adjust! ###` が付く。[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- 検出できない例: テーブル／列のリネーム（add+drop に見える）、無名制約、など。[autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)

→ プロジェクト Notes の「autogenerate を下書き → 人間が確認・修正してコミット」は公式どおり。

### 7. 起動時 auto upgrade（公式 Cookbook の経路）

- アプリから `alembic.command.upgrade(cfg, "head")` を呼べる。接続を共有するなら `Config.attributes["connection"]` を渡し、`env.py` がそれを優先する。[Cookbook — Sharing a Connection](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-across-one-or-more-programmatic-migration-commands)
- 失敗時の起動中止はアプリ側ポリシー（公式は「どう失敗を扱うか」までは規定しない）。downgrade を CLI のみにするのもアプリ／運用の選択で、Alembic 自体は `upgrade`/`downgrade` 両方を提供。

## Recommended layout for this repo (doc-backed)

```
repo/
  alembic.ini                 # script_location 等; URL はプレースホルダ可
  alembic/                    # または migrations/ 等（名前任意）
    env.py                    # DSJ_DB_PATH → sqlite URL; target_metadata; render_as_batch=True
    script.py.mako
    versions/                 # スキーマ正本（revision）
  src/daily_stock_judgment/
    ... schema module ...     # MetaData + Table のみ（置き場所は issue 02）
```

手順の骨格:

1. `alembic init alembic`（generic）。
2. アプリパッケージに Core `MetaData`/`Table` を置き、`env.py` で import → `target_metadata`。
3. `env.py` で `DSJ_DB_PATH` / 既定 `data/app.db` から URL を設定。`render_as_batch=True`。
4. `alembic revision --autogenerate -m "..."` → 人手修正 → コミット。
5. 起動時は Cookbook どおり `command.upgrade(..., "head")`；downgrade は CLI のみ。

## Non-goals / open

- MetaData モジュールの具体パス（`infrastructure` 配下の名前等）→ issue `02-metadata-placement`。
- baseline / stamp 既存 `app.db` → issue `04`。
- ストアの `CREATE TABLE IF NOT EXISTS` 削除タイミング → 実装フェーズ。

## Citations (primary)

| Claim | URL |
| --- | --- |
| autogenerate = MetaData vs DB; hand review | https://alembic.sqlalchemy.org/en/latest/autogenerate.html |
| `target_metadata: MetaData \| Sequence[MetaData]` | https://alembic.sqlalchemy.org/en/latest/api/runtime.html |
| env.py カスタム・URL を env var から | https://alembic.sqlalchemy.org/en/latest/tutorial.html |
| Core MetaData / Table | https://docs.sqlalchemy.org/en/20/core/metadata.html |
| SQLite URL 相対/絶対 | https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#connect-strings |
| `render_as_batch=True` | https://alembic.sqlalchemy.org/en/latest/batch.html |
| programmatic `command.upgrade` + shared connection | https://alembic.sqlalchemy.org/en/latest/cookbook.html |
