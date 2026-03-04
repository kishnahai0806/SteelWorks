"""Shared pytest fixtures for integration and e2e tests."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

import psycopg
import pytest
from dotenv import load_dotenv

from app.repository import OperationsRepository
from app.service import OperationsMetricsService

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_DATABASE_URL = (
    "postgresql+pg8000://postgres:postgres@127.0.0.1:55432/markdown_demo_test"
)
TEST_DB_CONTAINER_NAME = "markdown-demo-test-db"
TEST_DB_DOCKER_IMAGE = "postgres:17-alpine"


def _to_psycopg_url(sqlalchemy_url: str) -> str:
    if sqlalchemy_url.startswith("postgresql+pg8000://"):
        return sqlalchemy_url.replace("postgresql+pg8000://", "postgresql://", 1)
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _wait_for_database(psycopg_url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with (
                psycopg.connect(psycopg_url, connect_timeout=2) as conn,
                conn.cursor() as cur,
            ):
                cur.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise RuntimeError("Timed out waiting for database readiness.")


def _start_local_postgres_container() -> None:
    subprocess.run(
        ["docker", "rm", "-f", TEST_DB_CONTAINER_NAME],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "docker",
            "run",
            "--name",
            TEST_DB_CONTAINER_NAME,
            "-e",
            "POSTGRES_USER=postgres",
            "-e",
            "POSTGRES_PASSWORD=postgres",
            "-e",
            "POSTGRES_DB=markdown_demo_test",
            "-p",
            "55432:5432",
            "-d",
            TEST_DB_DOCKER_IMAGE,
        ],
        check=True,
    )


def _stop_local_postgres_container() -> None:
    subprocess.run(
        ["docker", "rm", "-f", TEST_DB_CONTAINER_NAME],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _load_sql_script(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _reset_schema_and_seed(psycopg_url: str) -> None:
    schema_sql = _load_sql_script(REPO_ROOT / "db" / "schema.sql")
    seed_sql = _load_sql_script(REPO_ROOT / "db" / "seed.sql")
    with psycopg.connect(psycopg_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(schema_sql)
        cur.execute(seed_sql)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    load_dotenv(REPO_ROOT / ".env.test", override=False)
    preferred = os.getenv("TEST_DATABASE_URL", "").strip()
    slide_name = os.getenv("DATABASE_URL_TEST", "").strip()
    if preferred:
        return preferred
    if slide_name:
        return slide_name
    return DEFAULT_TEST_DATABASE_URL


@pytest.fixture(scope="session")
def prepared_test_database(test_database_url: str) -> Generator[str]:
    parsed = urlparse(test_database_url)
    local_managed_db = (
        parsed.hostname in {"localhost", "127.0.0.1"}
        and parsed.port == 55432
        and parsed.path.strip("/") == "markdown_demo_test"
    )

    # This fixture drops/recreates schema; protect against accidental prod URLs.
    if not local_managed_db and "test" not in parsed.path.strip("/").lower():
        raise RuntimeError(
            "Refusing to run destructive test setup on non-test database name. "
            "Set TEST_DATABASE_URL to a dedicated test DB."
        )

    if local_managed_db:
        _start_local_postgres_container()

    psycopg_url = _to_psycopg_url(test_database_url)
    _wait_for_database(psycopg_url=psycopg_url)
    _reset_schema_and_seed(psycopg_url=psycopg_url)

    try:
        yield test_database_url
    finally:
        if local_managed_db:
            _stop_local_postgres_container()


@pytest.fixture()
def db_service(prepared_test_database: str) -> OperationsMetricsService:
    repository = OperationsRepository.from_database_url(prepared_test_database)
    return OperationsMetricsService(repository=repository)
