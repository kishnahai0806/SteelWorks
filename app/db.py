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
from typing import Any, Generator, Sequence

import pandas as pd
import psycopg
from psycopg.rows import dict_row


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
    # Prefer explicit user input so the UI can point to any environment quickly.
    candidate_url = (override_url or "").strip()
    if candidate_url:
        return candidate_url

    # Fall back to the process environment for local dev / CI convenience.
    env_url = (os.getenv("DATABASE_URL") or "").strip()
    if env_url:
        return env_url

    raise ValueError(
        "DATABASE_URL is not set. Provide a URL in the sidebar or export DATABASE_URL."
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

