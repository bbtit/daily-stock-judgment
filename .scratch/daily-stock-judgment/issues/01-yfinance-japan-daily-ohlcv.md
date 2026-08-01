# yfinanceは日本株の日足取得に足りるか

Type: research
Status: resolved

## Question

個人が日次で、登録した日本株（Yahoo Finance の `.T` ティッカー等）の四本値と出来高を取る前提で、yfinance はカバレッジ・遅延・利用上の制約の点で足りるか。足りない場合の現実的な代替は何か。

## Answer

**条件付きで足りる。** 東証の `.T` ティッカーから日足 OHLCV は取得できる（実測: `7203.T` 等）。場中は約20分遅延だが大引け後ジョブなら実用上問題になりにくい。ただし非公式経路・レート制限・Yahoo 規約上の自動化リスクがあり SLA はない。安定性や規約準拠を優先するなら **J-Quants Light 以上**（当日 OHLC・約16:30更新）が現実的な代替。

詳細: [.scratch/daily-stock-judgment/research/yfinance-japan-daily-ohlcv.md](../research/yfinance-japan-daily-ohlcv.md)
