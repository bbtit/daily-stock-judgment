# 起動時upgradeとCLIの形はどうするか

Type: grilling
Status: open
Blocked by: 01

## Question

起動時自動 `upgrade` の呼び出し境界（例: composition root）と、人が叩く CLI の形（`uv run alembic ...` 直か、プロジェクトスクリプト経由か）を決める。失敗時は起動中止、downgrade は CLI のみ、という好みは Notes 済み。
