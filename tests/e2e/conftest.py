"""Playwright e2e fixtures for running Streamlit against the test database."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
STREAMLIT_BASE_URL = "http://127.0.0.1:8510"


def _wait_for_streamlit(base_url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(base_url, timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError("Timed out waiting for Streamlit to start.")


@pytest.fixture(scope="session")
def streamlit_server_url(
    prepared_test_database: str, test_database_url: str
) -> Generator[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = test_database_url
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["PYTHONPATH"] = str(REPO_ROOT)

    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.port=8510",
            "--server.headless=true",
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_streamlit(base_url=STREAMLIT_BASE_URL)
        yield STREAMLIT_BASE_URL
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
