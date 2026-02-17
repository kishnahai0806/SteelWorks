"""
Database utility module for the Operations Issue Metrics Dashboard.

Why this module exists:
- Centralize database URL resolution.
- Centralize connection lifecycle handling.
- Provide one safe helper for running read queries and returning pandas DataFrames.

Resource management:
- Every connection and cursor is wrapped in a context manager and closed
  deterministically, so sockets/file descriptors are not leaked.

Complexity summary:
- URL resolution is O(1) time / O(1) space.
- A query execution is O(r * c) time to materialize `r` rows with `c` columns
  into a DataFrame, and O(r * c) space for the in-memory result.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Sequence
from urllib.parse import urlsplit

import pandas as pd
import psycopg
from psycopg.rows import dict_row

_ENV_LOADED = False
_ENV_DATABASE_URL: str | None = None


def _load_database_url_from_dotenv() -> str | None:
    """
    Load `DATABASE_URL` from project `.env` file.

    Behavior:
    - Reads only project-root `.env` (next to README/db/app folders).
    - Parses `KEY=VALUE` lines, ignores blank lines and comments.
    - Caches the result after first read.

    Complexity:
    - Time: O(n) where `n` is number of lines in `.env`.
    - Space: O(1) additional space beyond temporary line strings and one cached URL.
    """
    global _ENV_LOADED, _ENV_DATABASE_URL
    if _ENV_LOADED:
        return _ENV_DATABASE_URL
    _ENV_LOADED = True

    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    if not dotenv_path.exists():
        return None

    # `utf-8-sig` gracefully handles UTF-8 files with BOM (common on Windows).
    for raw_line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip('"').strip("'")

        if normalized_key == "DATABASE_URL" and normalized_value:
            _ENV_DATABASE_URL = normalized_value
            return _ENV_DATABASE_URL

    return None


def _validate_database_url(raw_url: str, source_name: str) -> str:
    """
    Validate URL shape early and return normalized value.

    Why this helper exists:
    - Prevent low-level socket/idna tracebacks for malformed placeholder URLs.
    - Return clear, actionable messages to the user.

    Complexity:
    - Time: O(m) where `m` is the URL length.
    - Space: O(1).
    """
    normalized_url = raw_url.strip().strip('"').strip("'")
    if not normalized_url:
        raise ValueError(f"DATABASE_URL from {source_name} is empty.")

    parsed = urlsplit(normalized_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError(
            f"DATABASE_URL from {source_name} must start with postgresql:// or postgres://."
        )
    if not parsed.hostname:
        raise ValueError(
            f"DATABASE_URL from {source_name} is malformed (host is missing)."
        )
    if "..." in normalized_url:
        raise ValueError(
            f"DATABASE_URL from {source_name} looks like a placeholder; replace '...' with your real host."
        )

    return normalized_url


def resolve_database_url(override_url: str | None) -> str:
    """
    Resolve the database URL using explicit input first, then `DATABASE_URL`.

    Args:
        override_url: URL typed by the user in the UI (may be `None` or empty).

    Returns:
        A non-empty PostgreSQL connection string.

    Raises:
        ValueError: If neither `override_url` nor environment `DATABASE_URL` exists.

    Complexity:
    - Time: O(1) because it performs constant-time string checks and one env lookup.
    - Space: O(1) because it stores only a few scalar values.
    """
    # 1) Prefer explicit user input so callers can override quickly when needed.
    candidate_url = (override_url or "").strip()
    if candidate_url:
        return _validate_database_url(candidate_url, "explicit input")

    # 2) Prefer local `.env` value to avoid stale shell env vars overriding local setup.
    dotenv_url = _load_database_url_from_dotenv()
    if dotenv_url:
        return _validate_database_url(dotenv_url, ".env")

    # 3) Fall back to process env for CI / deployment.
    env_url = (os.getenv("DATABASE_URL") or "").strip()
    if env_url:
        return _validate_database_url(env_url, "process environment")

    raise ValueError(
        "DATABASE_URL is not set. Add it to .env or export it in your shell."
    )


@contextmanager
def open_connection(
    database_url: str,
) -> Generator[psycopg.Connection[dict[str, Any]], None, None]:
    """
    Open a PostgreSQL connection and guarantee closure.

    Args:
        database_url: PostgreSQL connection string.

    Yields:
        A psycopg connection configured to return rows as dictionaries.

    Complexity:
    - Time: O(1) from Python's perspective (network handshake cost is external).
    - Space: O(1) for the connection handle.
    """
    # `row_factory=dict_row` makes query rows self-describing and conversion-friendly.
    connection: psycopg.Connection[dict[str, Any]] = psycopg.connect(
        database_url,
        row_factory=dict_row,
    )
    try:
        yield connection
    finally:
        # Explicit close avoids lingering TCP sockets if callers raise exceptions.
        connection.close()


def run_query(
    database_url: str,
    sql: str,
    params: Sequence[Any] | None = None,
) -> pd.DataFrame:
    """
    Execute a SELECT query and return results as a pandas DataFrame.

    Args:
        database_url: PostgreSQL connection string.
        sql: SQL statement with DB-API placeholders (`%s`).
        params: Optional positional bind parameters.

    Returns:
        DataFrame with SQL result rows. Empty DataFrame with the correct columns
        if the query returns no rows.

    Complexity:
    - Time: O(r * c) to transform `r` rows and `c` columns into DataFrame form.
    - Space: O(r * c) because results are materialized in memory.
    """
    with open_connection(database_url) as connection:
        # Cursor is also a context manager, so server-side resources are released.
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()

            # Column metadata is needed when result sets are empty.
            column_names = [
                column.name for column in (cursor.description or [])
            ]

    # Build DataFrame outside the connection block after all DB resources are closed.
    if not rows:
        return pd.DataFrame(columns=column_names)
    return pd.DataFrame.from_records(rows, columns=column_names)
