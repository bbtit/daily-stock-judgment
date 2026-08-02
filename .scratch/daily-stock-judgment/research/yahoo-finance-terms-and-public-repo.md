# Yahoo Finance / yfinance 利用条件と公開リポジトリの整理

> 調査日: 2026-08-02  
> 対象: Yahoo Finance の市場データを `yfinance` 等の非公式クライアントで利用する、個人向け localhost の日本株判断ツール。  
> 注意: これは一次資料の利用条件を要約した技術・運用メモであり、法的助言ではない。利用開始前に最新の規約と、必要なら専門家・データ提供者を確認すること。

## 結論の先取り

`yfinance` を Apache-2.0 の Python 依存関係として使い、**アプリケーションのソースコードだけ**を公開 GitHub リポジトリに置くこと自体は、Yahoo Finance の市場データを再配布する行為とは別である。ただし、公開コードが実行時に Yahoo Finance から自動取得するなら、実行者ごとの取得は Yahoo の自動取得禁止条項に依然として触れ得る。個人の localhost 利用、低頻度アクセス、データを Git に入れないことは配布・公開のリスクを小さくするが、Yahoo の「明示的な事前許可なく、**いかなる目的でも**自動手段でデータを収集してはならない」という条件の許可にはならない。

## 1. 自動アクセス・スクレイピング

### Yahoo の一般利用規約

Yahoo Terms of Service の Member conduct は、次を禁止している。

> “access or collect data ... using any automated means ... including ... robots, spiders, scrapers, data mining tools ... **for any purpose without our express, prior permission**.”

したがって、`yfinance` が HTTP API 呼出し・公開エンドポイントを利用する実装であっても、Yahoo の明示的な事前許可がない限り、Yahoo の規約文言上は自動取得に該当し得る。個人利用・localhost・非商用は、この「for any purpose」の例外として書かれていない。

また、Yahoo は「提供するインターフェースと指示以外の方法」でのアクセスや、商用目的でのアクセス／再利用も原則として禁止している。

> “You must not misuse or interfere with the Services or try to access them using a method other than the interface and the instructions that we provide.”  
> “Unless otherwise expressly stated, you may not access or reuse the Services ... for any commercial purpose.”

**含意:** Yahoo が公式に提供・許諾した API 契約や書面許可を持たない `yfinance` 依存の自動取得は、規約適合と断言できない。間隔を空ける、キャッシュする、レートを抑えることは運用負荷を下げる策であり、規約上の許可を代替しない。

**一次資料**

- Yahoo, *Terms of Service*, §6 Member conduct / Use of Services  
  https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html （取得日 2026-08-02）

### yfinance 自身の位置付け

`yfinance` の公式 README は、同ライブラリを Yahoo による公式製品と説明していない。

> “yfinance is **not** affiliated, endorsed, or vetted by Yahoo, Inc.”  
> “It’s an open-source tool that uses Yahoo’s publicly available APIs, and is intended for research and educational purposes.”  
> “Remember - the Yahoo! finance API is intended for personal use only.”

README 自身も、実際にダウンロードしたデータを使う権利は Yahoo の規約を確認するよう求めている。

> “You should refer to Yahoo!’s terms of use ... for details on your rights to use the actual data downloaded.”

**含意:** 「personal use only」は yfinance プロジェクトの注意書きであり、Yahoo の自動取得に対する明示的事前許可を証明するものではない。

**一次資料**

- yfinance, *README.md*  
  https://github.com/ranaroussi/yfinance/blob/main/README.md （取得日 2026-08-02）

## 2. 市場データの保存・表示・再配布

Yahoo の規約は、データを含む Yahoo の素材について、競合・実質的代替となるデータベース、アーカイブ、モバイルアプリ、データフィード、ウィジェットその他の集約データ源を作ることを禁止している。

> “use any material or content from, including without limitation any data, ... to create any database, archive, mobile application, data feed, widget or any other aggregated data source that competes with or constitutes a material substitute for the Services ... or the services offered by our data providers”

さらに、明示的な書面許可なしには、サービス／コンテンツ等の複製、変更、販売、配布、送信、放送、公開実演などを含む商用利用を禁止している。

> “Unless you have explicit written permission, you must not reproduce, modify, rent, lease, sell, trade, **distribute, transmit, broadcast, publicly perform**, create derivative works based on, or exploit for any commercial purposes, any portion or use of, or access to, the Services (including content, advertisements, APIs, and software).”

**保存:** localhost の一時キャッシュやローカル DB も「collect data」の結果であり、自動取得の問題からは独立しない。他者へ公開しない小規模な保存は、公開データフィード等とは事実関係が異なるが、Yahoo から一般的な保存許諾を得たことを意味しない。

**表示:** 自分だけが localhost で閲覧する表示は、インターネットで他者へ配信する表示とは異なる。一方で、Yahoo データを使う以上、取得の可否は別途残る。外部公開・共有・埋込み・CSV 配布・API 化は、配布／送信およびデータベース・フィードの条項との関係でリスクが大きい。

**再配布:** Git、GitHub Releases、静的サイト、公開 API、画面キャプチャの継続公開、コミット済み CSV/Parquet/SQLite は、単なるコード公開より明確に市場データの公開・配布に近づく。競合・実質的代替に至る態様は規約で明示的に禁止され、その他の再配布可否もデータ提供者の権利を含めて Yahoo の一般規約だけで判断しないこと。

**一次資料**

- Yahoo, *Terms of Service*, §6 Member conduct / Ownership and Reuse  
  https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html （取得日 2026-08-02）

## 3. 「個人 localhost」の位置付け

次の構成は、公開・再配布の範囲を意図的に狭める。

- localhost にのみ bind し、認証なしの外部公開 URL、公開 API、共有ダッシュボードを作らない
- 取得済み CSV、OHLCV、財務値、銘柄一覧、画像、SQLite/Parquet、キャッシュを Git に追加しない
- `gitignore` でデータ・キャッシュ・出力を除外する
- ツール上に「投資助言ではない」「データの正確性・遅延は保証しない」と表示する

しかしこれらは**リスク低減策であって許諾ではない**。Yahoo の自動取得禁止は “for any purpose” と記載されており、個人 localhost という利用場面を明文で除外していない。yfinance の “personal use only” 注意書きも同じく、Yahoo の規約を置き換えない。

## 4. 公開 GitHub リポジトリに「コードのみ」を置く場合

### コード公開が意味すること

アプリ独自のソースコード、依存関係宣言、データを含まないテスト fixture、取得方法を記した設定例を公開しても、通常それ自体は Yahoo 市場データを配布しているわけではない。`yfinance` 自体は Apache License 2.0 で配布されている。

> “each Contributor hereby grants to You a perpetual, worldwide, non-exclusive, no-charge, royalty-free ... copyright license to reproduce ... publicly display ... sublicense, and distribute the Work”

ただし Apache-2.0 が許諾する対象は **yfinance のコード**であり、Yahoo Finance のデータ、商標、API へのアクセス権、データ提供者の権利ではない。README も、Yahoo の商標であること、Yahoo と提携・承認・審査関係にないことを明記する。

> “Yahoo!, Y!Finance, and Yahoo! finance are registered trademarks of Yahoo, Inc.”  
> “yfinance is not affiliated, endorsed, or vetted by Yahoo, Inc.”

**コード公開時の実務上の線引き**

- 可視化・判定ロジック、`requirements`、`Ticker("7203.T")` のようなコード例は、市場データそのものではない。
- 実データを含む fixture、サンプル CSV、ダウンロード済みのデータベース、公開結果ページは含めない。
- 「Yahoo の公式ツール」「Yahoo に承認済み」と読める名称・説明・ロゴ使用を避ける。
- README に「利用者自身が Yahoo の最新規約、データ提供者条件、適用法を確認すること」「データはリポジトリに含めないこと」を明記する。
- 公開コードを他者が実行する場合も、取得リクエストは各実行者から Yahoo へ発生する。コード公開は、実行時アクセスの規約問題を解消しない。

**一次資料**

- yfinance, *LICENSE.txt* (Apache License 2.0, §§2, 4)  
  https://github.com/ranaroussi/yfinance/blob/main/LICENSE.txt （取得日 2026-08-02）
- yfinance, *README.md*  
  https://github.com/ranaroussi/yfinance/blob/main/README.md （取得日 2026-08-02）

## 5. 日本株・`.T` のデータ提供者注記

Yahoo Finance Help の取引所・データ提供者一覧では、日本の Tokyo Stock Exchange について次のように記載している。

> “Japan | Tokyo Stock Exchange | .T | 20 min | ICE Data Services”

同じ表では Nikkei Indices を “30 min” としている。

> “Japan | Nikkei Indices | N/A | 30 min | ICE Data Services”

**含意:**

- `.T` は Yahoo Finance 上で東京証券取引所を表すサフィックスである。
- 同ヘルプの表では、データ提供者は ICE Data Services、表示遅延は 20 分とされている。リアルタイム価格や取引執行判断に使う前提にしない。
- このデータ提供者注記は、ICE Data Services または取引所データの再配布許諾を Yahoo が付与したという意味ではない。配布・商用利用・外部サービス化が必要なら、該当提供者／取引所のライセンスを別途確認・取得する。

**一次資料**

- Yahoo Finance Help, *Exchanges and data providers on Yahoo Finance* (SLN2310)  
  https://help.yahoo.com/kb/finance/SLN2310.html （取得日 2026-08-02）

## 実用的な判定: 個人 localhost の日本株判断ツール

**公開ソースコードのみ（市場データをコミットしない）という構成は、Yahoo データを公開・再配布する構成よりは明確に低リスクであり、コード公開のためだけに Yahoo のデータ利用権が追加で必要になるとは、この資料群からは読めない。** ただし、これは「yfinance による取得が許可される」という結論ではない。Yahoo の現行 Terms は、明示的な事前許可なしの自動データ収集を目的を問わず禁止しているため、`yfinance` に依存する限り規約上のリスクは残る。

この個人ツールを続けるなら、少なくとも localhost 限定・最小頻度・短期キャッシュ・市場データの非コミット／非公開／非配布を守り、公開 README にデータを同梱しない方針と非公式クライアントである旨を記載する。**規約適合を必要条件にする場合は、Yahoo／データ提供者から書面許可を得るか、用途（日本株、保存・表示・公開範囲）に合う商用・公式ライセンスのデータ提供者へ切り替えるべきである。**
