"""
Bootstrap script to apply `db/schema.sql` and `db/seed.sql` to PostgreSQL.

Use case:
- The assignment asks to execute seed data on a Render PostgreSQL database.
- Many environments do not have `psql` installed, so this script applies SQL
  files through psycopg directly.

Resource management:
- Connections and cursors are enclosed in context managers to guarantee closure.

Complexity:
- Time: O(n) where `n` is the total SQL text size plus database execution cost.
- Space: O(n) for loading SQL file contents into memory.
"""

from __future__ import annotations

from pathlib import Path

import psycopg

from app.db import resolve_database_url


def _read_sql_file(file_path: Path) -> str:
    """
    Read a UTF-8 SQL file into memory.

    Complexity:
    - Time: O(n) for `n` bytes in the file.
    - Space: O(n) for the returned string.
    """
    return file_path.read_text(encoding="utf-8")


def _execute_sql(connection: psycopg.Connection, sql_text: str) -> None:
    """
    Execute one SQL script text block against the open connection.

    Complexity:
    - Time: O(m) in Python for dispatching script text of length `m`;
      overall runtime is dominated by database processing.
    - Space: O(1) additional Python memory beyond the SQL text itself.
    """
    # Cursor context manager ensures server-side statement resources are released.
    with connection.cursor() as cursor:
        cursor.execute(sql_text)


def main() -> None:
    """
    Resolve DATABASE_URL and apply schema then seed scripts in order.

    Complexity:
    - Time: O(n) for reading SQL files + database execution time.
    - Space: O(n) for SQL text strings.
    """
    try:
        # Reuse shared resolver so this script can read `.env` automatically.
        database_url = resolve_database_url(None)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc

    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "db" / "schema.sql"
    seed_path = repo_root / "db" / "seed.sql"

    schema_sql = _read_sql_file(schema_path)
    seed_sql = _read_sql_file(seed_path)

    # Autocommit is required because schema/seed scripts manage transactions explicitly.
    with psycopg.connect(database_url, autocommit=True) as connection:
        _execute_sql(connection, schema_sql)
        _execute_sql(connection, seed_sql)

    print("Successfully applied db/schema.sql and db/seed.sql")


if __name__ == "__main__":
    main()
