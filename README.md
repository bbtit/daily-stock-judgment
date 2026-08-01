# 日次売買判断

個人向け・日本株の大引け後日次判断ツール（localhost）。

## セットアップ / 起動

```bash
uv sync
uv run playwright install chromium
uv run pytest -q
uv run daily-stock-judgment
```

ブラウザ: http://127.0.0.1:8000  
SQLite のデフォルト保存先: `data/app.db`

### E2E（Playwright）

振る舞いをブラウザ経由で検証する。内部モジュールは import せず、URL とアクセシブル名だけで操作する（将来の FE/BE 分離後も `BASE_URL` を差し替えれば同じスイートを使える）。

```bash
uv run pytest e2e -q
# 既に起動中のアプリへ向ける場合:
BASE_URL=http://127.0.0.1:8000 uv run pytest e2e -q
```

## アーキテクチャ

実装方針（DDD / クリーンアーキテクチャ / イミュータブル）は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。

## ディレクトリ構成

依存は外側 → 内側（`domain`）へ向ける。ドメインの値はイミュータブル（frozen dataclass）。

```text
.
├── CONTEXT.md                 # ドメイン用語
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── data/                      # ローカル SQLite（*.db は gitignore）
├── tests/                     # ユースケース seam + SQLite 永続化 + Web
├── e2e/                       # Playwright（ブラウザ振る舞い）
├── .scratch/                  # 仕様・wayfinder（実装コード外）
└── src/daily_stock_judgment/
    ├── __main__.py            # CLI エントリ
    ├── composition.py         # 配線（DB パス・ストア・Web）
    ├── domain/                # エンティティ / VO / 純関数（外側依存なし）
    │   ├── ticker.py
    │   ├── holding.py
    │   ├── watchlist.py
    │   ├── bar.py
    │   ├── judgment.py
    │   ├── labeling.py
    │   └── result.py
    ├── application/           # ユースケース + ポート（Protocol）
    │   ├── ports.py
    │   ├── manage_instruments.py
    │   ├── run_daily_judgment.py
    │   └── validate_draft.py
    ├── infrastructure/        # アダプタ（SQLite / InMemory / テスト用フェイクは tests）
    │   ├── sqlite_instrument_store.py
    │   ├── memory_instrument_store.py
    │   ├── sqlite_judgment_store.py
    │   └── memory_judgment_store.py  # InMemoryJudgmentStore
    └── presentation/          # FastAPI + テンプレート
        ├── web.py
        └── templates/
```

### 層の役割

| 層 | 役割 |
| --- | --- |
| `domain` | `Ticker` / `Holding` など不変の値と純関数。`sqlite3` / FastAPI を import しない |
| `application` | `InstrumentBook` ポートとユースケース。副作用はポート経由 |
| `infrastructure` | ポートの実装（永続化・テスト用メモリ） |
| `presentation` | HTTP UI。ユースケースだけ呼ぶ |
| `composition` | 具体アダプタを組み立ててアプリを起動可能にする |
