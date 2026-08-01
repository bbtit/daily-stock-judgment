"""Playwright E2E fixtures.

These tests speak only HTTP + the browser. They do not import application
internals beyond launching the process. Point BASE_URL at any deployed stack
(including a future split frontend/backend) to reuse the same suite.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def app_url(tmp_path: Path) -> Iterator[str]:
    """Fresh app process + empty DB per test (or external BASE_URL)."""
    override = os.environ.get("BASE_URL")
    if override:
        yield override.rstrip("/")
        return

    port = _free_port()
    db_path = tmp_path / "app.db"
    env = {
        **os.environ,
        "DSJ_DB_PATH": str(db_path),
        # Fixed day + demo market so E2E stays offline and deterministic.
        "DSJ_AS_OF": "2026-07-31",
        "DSJ_MARKET": "demo",
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
