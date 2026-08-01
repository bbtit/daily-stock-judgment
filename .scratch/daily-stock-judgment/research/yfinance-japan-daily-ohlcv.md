# yfinance は日本株の日足 OHLCV 取得に足りるか

調査日: 2026-08-01  
対象チケット: [01-yfinance-japan-daily-ohlcv](../issues/01-yfinance-japan-daily-ohlcv.md)

## Verdict

**個人の日次（大引け後）ウォッチリスト用途では、機能面では足りる。**  
東証系の Yahoo Finance `.T` ティッカーから日足四本値・出来高は取得できる。一方で、公式契約のない非公式経路・レート制限・利用規約上の自動化リスクがある。運用の安定性や規約準拠を優先するなら **J-Quants API（JPX、有料 Light 以上）** が現実的な代替。

## Scope

個人が日次で、登録した日本株（例: `7203.T`）の四本値と出来高を取る前提。場中リアルタイムは対象外。

## Method

- 一次情報: yfinance 公式ドキュメント / GitHub、Yahoo Finance Help / Terms、J-Quants 公式サイト・API 仕様
- 実測: `yfinance==1.2.0` で `7203.T` 等の日足を取得（本調査時点）

---

## 1. 日足 OHLCV は取れるか

### 一次情報

- yfinance は Yahoo! finance の公開 API 経由で市場データを取る Python ライブラリ。[README](https://github.com/ranaroussi/yfinance/blob/main/README.md) / [docs](https://ranaroussi.github.io/yfinance/)
- `Ticker.history` / `download` は `interval='1d'` を明示的にサポート。[download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
- Yahoo Finance Help「Exchanges and data providers」は **Tokyo Stock Exchange のサフィックスを `.T`** と記載。[SLN2310](https://help.yahoo.com/kb/SLN2310.html)

### 実測（2026-08-01 UTC、土曜）

| ティッカー | 結果 | 直近営業日バー |
|---|---|---|
| `7203.T`（トヨタ） | OHLCV 取得可 | 2026-07-31, Close 3067.0, Volume 37342500 |
| `6758.T` / `9984.T` / `9432.T` | 同上 | 2026-07-31 |
| `8951.T`（REIT）/ `4385.T` / `1540.T`（ETF） | 同上 | 2026-07-31 |
| `9999.T`（架空） | 空 / delisted 扱い | — |

`history_metadata` / chart API 上、`exchangeName: JPX`、`currency: JPY`、タイムゾーン `Asia/Tokyo`。  
Yahoo chart API 例: `https://query1.finance.yahoo.com/v8/finance/chart/7203.T?interval=1d&range=5d`

**結論:** 登録銘柄が Yahoo 上で `.T` として存在する限り、日足 OHLCV は取得可能。

---

## 2. カバレッジとギャップ

| 点 | 根拠 | 含意 |
|---|---|---|
| 東証ティッカーは `.T` | [SLN2310](https://help.yahoo.com/kb/SLN2310.html) | 証券コードだけでは足りず、Yahoo 表記に合わせる |
| データ有無は Yahoo 側の掲載に依存 | yfinance bug template: 「Yahoo にデータがあるか確認せよ」([bug_report.yaml](https://raw.githubusercontent.com/ranaroussi/yfinance/main/.github/ISSUE_TEMPLATE/bug_report.yaml)) | 非上場・ティッカー誤り・Yahoo 未掲載は空になる |
| yfinance は Yahoo のラッパーであり保証者ではない | docs の legal disclaimer / bug template「yfinance is not affiliated with Yahoo」 | 欠測・誤りは Yahoo 側由来になり得る |
| J-Quants は「東証に上場していない銘柄は含まない」と明示 | [eq-bars-daily](https://jpx-jquants.com/en/spec/eq-bars-daily) | 公式代替でも東証外は別問題。yfinance も Yahoo 掲載範囲に閉じる |

ウォッチリスト規模（数十銘柄）の東証本則銘柄であれば、実務上のカバレッジは十分な見込み。全上場の完全網羅や Yahoo 未掲載銘柄までは期待しない。

---

## 3. 遅延（大引け後の日次利用）

### Yahoo Finance（yfinance が使う側）

- Tokyo Stock Exchange (`.T`): **20 min delay**、provider ICE Data Services。[SLN2310](https://help.yahoo.com/kb/SLN2310.html)
- 場中の「最新値」は最大約20分遅れ得る。大引け（15:00 JST）後に当日バーを使うなら、**概ね 15:20 以降**を見れば遅延枠は埋まる想定。
- 本調査の実測では、土曜時点で金曜（2026-07-31）の日足バーが取得できた。

### 参考: Yahoo!ファイナンス（日本、別サービス）

LINE ヤフーの Yahoo!ファイナンスは、日本株の**日足チャート更新が当日 20:30 ごろ**と案内。[チャートの更新タイミング](https://support.yahoo-net.jp/SccFinance/s/article/H000006627)  
これは `finance.yahoo.com` / yfinance 経路そのものではないが、「日本株の日足がすぐ確定しない場合がある」という運用上の注意材料。

### 運用示唆

大引け直後のバッチより、**15:30〜夜**に日次ジョブを置く方が安全。当日バー欠落時はリトライ。

---

## 4. レート制限・信頼性・利用制約

### yfinance / Yahoo

- yfinance 公式: **research and educational purposes**、Yahoo API は **personal use only** と明記。データ利用権は Yahoo の規約を見よ、と誘導。[docs index](https://ranaroussi.github.io/yfinance/) / [README](https://github.com/ranaroussi/yfinance/blob/main/README.md)
- Yahoo Developer API Terms: rate limits は Yahoo の裁量。[API Terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html)
- Yahoo Terms (OTOS): 許可なく automated means（robots / scrapers / data mining 等）でデータ収集することを禁止する条項あり。[Yahoo Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)
- yfinance メンテナ側 bug template: Yahoo free service に rate-limiting があり、超過すると delay / block / bad data になり得る。これは yfinance のバグではない、と案内。[bug_report.yaml](https://raw.githubusercontent.com/ranaroussi/yfinance/main/.github/ISSUE_TEMPLATE/bug_report.yaml) → [Discussion #1513](https://github.com/ranaroussi/yfinance/discussions/1513)  
  （議論内の具体数値は Yahoo Finance 公式ドキュメントとしては確定していない。DSP API の数値が誤引用された例もある。）

### Yahoo!ファイナンス（日本）との混同注意

日本の Yahoo!ファイナンスは、掲載情報のプログラムによる機械的取得（スクレイピング等）を禁止。[ヘルプ](https://support.yahoo-net.jp/SccFinance/s/article/H000011276)  
yfinance が叩くのは主に米 Yahoo Finance 系エンドポイントだが、「Yahoo 系ファイナンスの自動取得は規約上グレー／禁止寄り」というリスクは共有しておく。

### 信頼性の実務的読み

- ウォッチリスト数十銘柄・日次1回なら、レート制限に当たりにくい。
- ただし SLA なし。突然の 429 / 空データ / API 変更があり得る。
- 本番相当の個人ツールなら、空レスポンス検知・リトライ・キャッシュを前提にする。

---

## 5. 代替（一次情報ベース）

前提が「個人・日本株・日次 OHLCV」なら、最有力は **J-Quants API（日本取引所グループ）**。

| 項目 | 内容 | 出典 |
|---|---|---|
| 何か | 個人向けに株価・財務等を API 配信 | [J-Quants](https://jpx-jquants.com/en/) / [llms.txt](https://jpx-jquants.com/llms.txt) |
| 日足 | `GET /v2/equities/bars/daily`（O/H/L/C/Vo 等） | [eq-bars-daily](https://jpx-jquants.com/en/spec/eq-bars-daily) |
| 更新 | Stock Prices (OHLC) は **Daily / Around 16:30** | [data-update](https://jpx-jquants.com/en/spec/data-update) |
| Free | 2年履歴だが **12 weeks delayed**（当日不可） | [pricing / FAQ](https://jpx-jquants.com/en/) |
| Light | ¥1,650/月、5年、OHLC、60 calls/min | 同上 |
| 範囲 | 東証上場以外は含まない | [eq-bars-daily Attention](https://jpx-jquants.com/en/spec/eq-bars-daily) |
| 利用 | 個人投資家向け。商用等は規約で禁止 | [llms.txt](https://jpx-jquants.com/llms.txt) |

**日次判断ツールで「当日の大引け後データ」が要るなら Free では足りず、Light 以上が現実的。**

その他:

- **Yahoo!ファイナンス VIP 倶楽部の時系列DL**: 日本 Yahoo がスクレイピング禁止の代替として案内する公式ダウンロード。[スクレイピング禁止ヘルプ](https://support.yahoo-net.jp/SccFinance/s/article/H000011276) — API 向きではないが手動／半自動の退避先。
- 証券会社 API や有料データベンダー: 本調査では一次情報を深掘りしていない。個人ツールならコスト対効果で J-Quants が先。

---

## 6. 総合判断（チケットへの回答）

| 観点 | 判定 |
|---|---|
| カバレッジ | 東証 `.T` の日足 OHLCV は実測で取れる。Yahoo 未掲載は欠ける |
| 遅延 | 場中は約20分遅延。大引け後ジョブなら実用上問題になりにくい |
| 制約 | 個人・教育寄り、自動化は規約リスク、レート制限・突然の不通あり |
| 個人日次ツール | **足りる（条件付き）** — ウォッチリスト規模・大引け後・失敗時リトライ前提 |
| 足りない場合 | **J-Quants Light 以上**（公式・約16:30更新・当日 OHLC） |

仕様メモ（Destination）が「入力は日次の四本値と出来高（yfinance）」としている前提とも整合する。ただし仕様に書くなら、**非公式経路であること**と、必要なら **J-Quants への切替余地**を一文残すのがよい。

## Sources

1. https://ranaroussi.github.io/yfinance/
2. https://github.com/ranaroussi/yfinance/blob/main/README.md
3. https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html
4. https://raw.githubusercontent.com/ranaroussi/yfinance/main/.github/ISSUE_TEMPLATE/bug_report.yaml
5. https://github.com/ranaroussi/yfinance/discussions/1513
6. https://help.yahoo.com/kb/SLN2310.html
7. https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html
8. https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html
9. https://support.yahoo-net.jp/SccFinance/s/article/H000011276
10. https://support.yahoo-net.jp/SccFinance/s/article/H000006627
11. https://jpx-jquants.com/en/
12. https://jpx-jquants.com/llms.txt
13. https://jpx-jquants.com/en/spec/eq-bars-daily
14. https://jpx-jquants.com/en/spec/data-update
15. Empirical: `yfinance==1.2.0` against Yahoo chart/history APIs on 2026-08-01
