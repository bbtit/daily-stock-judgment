# 往復テストの置き場所と最小範囲は何か

Type: grilling
Status: resolved
Blocked by: 01, 03

## Question

upgrade↔downgrade 往復の自動テストをどこに置き、何を最小ケースとするか（一時 DB、base↔head、stamp 済みレガシー相当など）。アプリ機能テストとの分離方針を決める。

## Answer

`tests/test_alembic_migrations.py` に置く。最小ケースは空の一時 DB → `create_app`（起動時 upgrade）→ 4テーブル存在＋ストアの軽い読み書き。downgrade の自動テストはしない（CLI 能力は残す）。チャート時 Notes の「往復自動テスト」はこの決定で上書き。
