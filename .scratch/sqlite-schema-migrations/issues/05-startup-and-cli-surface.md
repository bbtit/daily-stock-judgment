# 起動時upgradeとCLIの形はどうするか

Type: grilling
Status: resolved
Blocked by: 01

## Question

起動時自動 `upgrade` の呼び出し境界（例: composition root）と、人が叩く CLI の形（`uv run alembic ...` 直か、プロジェクトスクリプト経由か）を決める。失敗時は起動中止、downgrade は CLI のみ、という好みは Notes 済み。

## Answer

起動時は `composition.create_app` 内で `prepare_db_path` の直後・ストア生成前に `upgrade head`。失敗は例外で起動中止。人が叩く CLI は `uv run alembic …` 直（専用ラッパなし）。`env.py` が `DSJ_DB_PATH` を解決。downgrade / stamp / revision は CLI のみ。
