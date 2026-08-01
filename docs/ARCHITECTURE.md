# Architecture

個人向け日次売買判断ツールの実装方針。用語は [`CONTEXT.md`](../CONTEXT.md) を正とする。プロダクト要件は [`.scratch/daily-stock-judgment/spec.md`](../.scratch/daily-stock-judgment/spec.md) を正とする。

## Goals

- 判断ロジックと永続化・HTTP を分離し、テストと差し替えを容易にする
- ドメインをイミュータブルに保ち、副作用を外側に閉じ込める
- 将来の日次判断ランナー（相場取得・エージェント CLI）を同じ層に載せられる形にする

## Style

**DDD（軽量）** — ユビキタス言語（判断・スコア・ラベル・理由・ウォッチリスト・保有）でモデルする。巨大な集約やイベントソーシングは採用しない。

**クリーンアーキテクチャ** — 依存は外側から内側（`domain`）へ。内側は外側のフレームワークを知らない。

**関数型のエッセンス（限定）** — 過剰な効果システムは使わない。次だけ守る。

- 値オブジェクトは `frozen=True` の dataclass
- ドメイン変換は純関数（入力 → 新しい値 / `Result`。その場ミューテーションなし）
- 永続化は「読む → 純関数で次状態 → 書く」、または行の置換。InMemory は状態オブジェクトの差し替え
- ドメイン／アプリケーションの失敗は小さな `Result`（`Ok` / `Err`）。Web 層でメッセージ化する

## Layers

```text
presentation  →  application  →  domain
      ↓               ↓
infrastructure（ports を実装）
composition（配線のみ）
```

| 層 | 置いてよいもの | 置いてはいけないもの |
| --- | --- | --- |
| `domain` | VO、純関数、`Result` | `sqlite3`、FastAPI、HTTP、環境変数 |
| `application` | ユースケース、`Protocol`（ポート） | 具象 DB / HTTP 詳細 |
| `infrastructure` | ポートのアダプタ（SQLite、InMemory、将来の yfinance / CLI） | ドメイン用語の再定義 |
| `presentation` | FastAPI、テンプレート、フォーム変換 | ビジネスルール本体 |
| `composition` | パス解決、具象の組み立て、`create_app` | ドメインロジック |

ディレクトリの一覧は [`README.md`](../README.md) を参照。

## Seams

テストと差し替えの主 seam は **アプリケーションユースケース + ポート**。

- 現状: `InstrumentBook` + `manage_instruments`
- 将来: 日次判断ランナー用ポート（相場取得・エージェント CLI）を同様に切る

ユースケースの単体テストは InMemory アダプタを使う。SQLite などインフラは永続化など少数の結合テストに留める。

## Persistence

- 正本はプロジェクトローカルの SQLite（デフォルト `data/app.db`）
- 上書きパスは環境変数 `DSJ_DB_PATH`
- スキーマ詳細はインフラの関心事。ドメインは `Ticker` / `Holding` などとしてだけ知る

## Out of scope for this document

発注連携、マルチテナント、Cloudflare、事後の当たり外れ検証などプロダクト Out of scope は spec / wayfinder マップ側に書く。ここには載せない。
