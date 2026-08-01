# 日次株価売買判断ツールの仕様

## Destination

個人が日次で使える、日本株の売買判断ツールの仕様。大引け後に、ウォッチリストと保有銘柄についてスコア（-100〜+100）・ラベル（買う／売る／様子見）・短い理由を一覧できること。入力は日次の四本値と出来高（yfinance）。判断エンジンは汎用LLM（専用学習モデルなし）。発注・数量提案は含めない。

## Notes

- ドメイン: 個人向け・日本株・日次判断。用語はリポジトリ根の `CONTEXT.md` を正とする。
- 毎セッション参照: `/grilling`, `/domain-modeling`, 必要なら `/research` と `/prototype`。
- 立ち位置の好み: 自分専用・localhost 一覧。ウォッチ／保有の正本は SQLite（画面 CRUD）。売るは保有のみ、買うはウォッチ／保有どちらも可。判断は提示まで。LLMはローカルのエージェント CLI（Cursor CLI・Claude Code 等）経由でスコアと理由、ラベルは閾値でシステム付与。株価履歴は直近60営業日（不足時は取れる分）。実行は手動が正（推奨 16:00〜21:00 JST）。Cloudflare Tunnel / Access は使わない。
- このマップは計画まで。仕様本文の執筆は、道が晴れてから別作業。

## Decisions so far

<!-- the index — one line per closed ticket: enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [yfinanceは日本株の日足取得に足りるか](.scratch/daily-stock-judgment/issues/01-yfinance-japan-daily-ohlcv.md) — 個人の大引け後日次なら足りる（.T日足可・20分遅延）。規約/安定性を取るならJ-Quants Light以上
- [スコアからラベルへの変換ルールは何か](.scratch/daily-stock-judgment/issues/02-score-to-label-thresholds.md) — 固定閾値（≥+50買う、≤−50売る／未保有は様子見、他は様子見）。ラベルはシステム付与
- [LLMに渡す株価履歴の期間はどのくらいか](.scratch/daily-stock-judgment/issues/03-price-history-lookback.md) — 直近60営業日（共通）。不足分は取れるだけ渡す
- [短い理由に必須の要素は何か](.scratch/daily-stock-judgment/issues/04-reason-requirements.md) — 観察必須（終値の水準／変化）・解釈任意・約200字・禁止表現あり。ラベル語禁止、符号不一致は再生成1回後エラー
- [どのLLMプロバイダとモデルを前提にするか](.scratch/daily-stock-judgment/issues/05-llm-provider-premise.md) — 遵守優先。ローカルエージェントCLI経由（製品・モデル名は固定しない）。切替UIなし。一覧はlocalhost
- [ウォッチリストと保有はどう登録・更新するか](.scratch/daily-stock-judgment/issues/06-watchlist-holdings-ux.md) — SQLite正本＋画面CRUD。数量任意。日次は追加削除・保有登録解除・一覧閲覧
- [大引け後ジョブの時刻と休場日はどうするか](.scratch/daily-stock-judgment/issues/07-after-close-schedule.md) — 手動正・OS自動は任意。推奨16–21時JST。休場は新規判断なし。欠落は再実行可
- [LLMの入出力スキーマとプロンプト骨子は何か](.scratch/daily-stock-judgment/issues/10-llm-io-schema-prompt.md) — 1銘柄1回。出:{ticker,score,reason} 入:ticker/as_of/holding/bars。指示+JSON。事後検証あり
- [データ欠落とLLM失敗時の扱いは何か](.scratch/daily-stock-judgment/issues/09-data-and-llm-failure-handling.md) — 部分成功可。データ未着/取得不可/判断失敗。リトライ有、捏造なし
- [判断履歴の保存・振り返りを仕様にどこまで書くか](.scratch/daily-stock-judgment/issues/11-judgment-history-scope.md) — 成功判断をSQLite保存・無期限。過去日一覧まで。同日は上書き。失敗は残さない
- [コスト上限の扱いは何か](.scratch/daily-stock-judgment/issues/12-cost-cap-handling.md) — 仕様に上限は書かない。コストはCLI/サブスクの運用任せ

## Not yet specified

## Out of scope

- 発注連携・推奨数量・自動売買
- 専用の学習モデルや手書きテクニカルルールを本体にする方式
- 複数ユーザー・共有利用
- 日本株以外の市場、市場全体からの候補出し
- ニュース・財務・板情報などの非・日足データ
- 寄り付き前・場中の判断
- Cloudflare Tunnel / Access — localhost 前提のため不要（[Cloudflare Accessの認証手段は何か](.scratch/daily-stock-judgment/issues/08-cloudflare-access-idp.md)）
- 事後の当たり外れ検証（バックテスト・勝率集計等）— 判断一覧が目的のため（[事後の当たり外れ検証を仕様に含めるか](.scratch/daily-stock-judgment/issues/13-outcome-evaluation-scope.md)）
