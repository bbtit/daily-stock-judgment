"""過去日の判断一覧のブラウザ振る舞い。"""

from __future__ import annotations

import os
import socket
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _seed_past_judgment(db_path: Path) -> None:
    """Seed via SQL only — no application package imports."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS judgments (
                ticker TEXT NOT NULL COLLATE NOCASE,
                as_of TEXT NOT NULL,
                score INTEGER NOT NULL,
                label TEXT NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY (ticker, as_of)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO judgments (ticker, as_of, score, label, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "7203.T",
                "2026-07-30",
                62,
                "買う",
                "終値3200円付近で前日比高寄り。",
            ),
        )


@pytest.fixture
def history_app_url(tmp_path: Path) -> Iterator[str]:
    """App with one past successful judgment already saved."""
    override = os.environ.get("BASE_URL")
    if override:
        yield override.rstrip("/")
        return

    port = _free_port()
    db_path = tmp_path / "app.db"
    _seed_past_judgment(db_path)
    env = {
        **os.environ,
        "DSJ_DB_PATH": str(db_path),
        "DSJ_AS_OF": "2026-07-31",
        "DSJ_MARKET": "demo",
        "DSJ_JUDGMENT_MODEL": "demo",
        "PYTHONPATH": os.pathsep.join(
            [str(SRC), *(p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p)]
        ),
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "daily_stock_judgment.composition:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    try:
        while time.time() < deadline:
            if proc.poll() is not None:
                out = proc.stdout.read() if proc.stdout else ""
                raise RuntimeError(
                    f"uvicorn exited before becoming ready (code={proc.returncode}):\n{out}"
                )
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            out = ""
            if proc.stdout:
                proc.terminate()
                out = proc.stdout.read()
            raise RuntimeError(f"uvicorn did not accept connections in time:\n{out}")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_過去日を選んだとき成功判断が一覧に出る(
    page: Page, history_app_url: str
) -> None:
    page.goto(f"{history_app_url}/")

    form = page.get_by_role("form", name="過去の判断日を選ぶ")
    form.get_by_label("過去の判断日").select_option("2026-07-30")
    form.get_by_role("button", name="表示").click()

    results = page.get_by_role("list", name="過去の判断結果")
    expect(results.get_by_role("listitem")).to_contain_text("7203.T")
    expect(results.get_by_role("listitem")).to_contain_text("スコア")
    expect(results.get_by_role("listitem")).to_contain_text("買う")
    expect(results.get_by_role("listitem")).to_contain_text(
        "終値3200円付近で前日比高寄り。"
    )
