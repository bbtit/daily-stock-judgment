# 日次株価売買判断ツールの仕様

## Destination

個人が日次で使える、日本株の売買判断ツールの仕様。大引け後に、ウォッチリストと保有銘柄についてスコア（-100〜+100）・ラベル（買う／売る／様子見）・短い理由を一覧できること。入力は日次の四本値と出来高（yfinance）。判断エンジンは汎用LLM（専用学習モデルなし）。発注・数量提案は含めない。

## Notes

- ドメイン: 個人向け・日本株・日次判断。用語はリポジトリ根の `CONTEXT.md` を正とする。
- 毎セッション参照: `/grilling`, `/domain-modeling`, 必要なら `/research` と `/prototype`。
- 立ち位置の好み: 自分専用Web一覧。デプロイは Cloudflare Tunnel + Cloudflare Access。売るは保有のみ、買うはウォッチ／保有どちらも可。判断は提示まで。
- このマップは計画まで。仕様本文の執筆は、道が晴れてから別作業。

## Decisions so far

<!-- the index — one line per closed ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [yfinanceは日本株の日足取得に足りるか](.scratch/daily-stock-judgment/issues/01-yfinance-japan-daily-ohlcv.md) — 個人の大引け後日次なら足りる（.T日足可・20分遅延）。規約/安定性を取るならJ-Quants Light以上

## Not yet specified

- LLMへ渡すプロンプトと入出力スキーマの詳細（モデル・履歴長・理由の要件が固まってから）
- 判断履歴の保存・振り返りを仕様にどこまで書くか
- コスト上限・失敗時（データ欠落、LLMエラー）の扱い
- 事後の当たり外れ検証（バックテストやログ評価）を仕様に含めるか

## Out of scope

- 発注連携・推奨数量・自動売買
- 専用の学習モデルや手書きテクニカルルールを本体にする方式
- 複数ユーザー・共有利用
- 日本株以外の市場、市場全体からの候補出し
- ニュース・財務・板情報などの非・日足データ
- 寄り付き前・場中の判断
