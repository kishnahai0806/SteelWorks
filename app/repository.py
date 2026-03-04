"""Database repository for operations analytics queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine


class OperationsRepository:
    """Read-side repository backed by PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_database_url(cls, database_url: str) -> OperationsRepository:
        normalized_url = cls._normalize_database_url(database_url)
        engine = create_engine(normalized_url, future=True)
        return cls(engine=engine)

    @staticmethod
    def _normalize_database_url(database_url: str) -> str:
        """Normalize incoming Postgres URLs to an explicit SQLAlchemy driver."""
        trimmed = database_url.strip()
        if trimmed.startswith("postgres://"):
            return trimmed.replace("postgres://", "postgresql+pg8000://", 1)
        if trimmed.startswith("postgresql://"):
            return trimmed.replace("postgresql://", "postgresql+pg8000://", 1)
        if trimmed.startswith("postgresql+psycopg://"):
            return trimmed.replace("postgresql+psycopg://", "postgresql+pg8000://", 1)
        return trimmed

    def get_available_weeks(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
              calendar_week_id,
              week_label
            FROM calendar_weeks
            ORDER BY start_date
            """
        )
        return self._fetch_all(statement=statement, params={})

    def get_available_lines(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
              production_line_id,
              line_name,
              is_active
            FROM production_lines
            WHERE is_active = TRUE
            ORDER BY line_name
            """
        )
        return self._fetch_all(statement=statement, params={})

    def get_issue_summary(
        self, week_id: int, line_ids: list[int], group_by_line: bool
    ) -> list[dict[str, Any]]:
        if not line_ids:
            return []

        if group_by_line:
            sql = """
                SELECT
                  cw.week_label,
                  pl.line_name,
                  it.issue_type_name,
                  COUNT(*)::integer AS issue_count
                FROM production_issues pi
                JOIN production_runs pr ON pr.production_run_id = pi.production_run_id
                JOIN issue_types it ON it.issue_type_id = pi.issue_type_id
                JOIN calendar_weeks cw ON cw.calendar_week_id = pr.calendar_week_id
                JOIN production_lines pl
                  ON pl.production_line_id = pr.production_line_id
                WHERE pr.calendar_week_id = :week_id
                  AND pr.production_line_id IN :line_ids
                GROUP BY cw.week_label, pl.line_name, it.issue_type_name
                ORDER BY pl.line_name, it.issue_type_name
            """
        else:
            sql = """
                SELECT
                  cw.week_label,
                  it.issue_type_name,
                  COUNT(*)::integer AS issue_count
                FROM production_issues pi
                JOIN production_runs pr ON pr.production_run_id = pi.production_run_id
                JOIN issue_types it ON it.issue_type_id = pi.issue_type_id
                JOIN calendar_weeks cw ON cw.calendar_week_id = pr.calendar_week_id
                WHERE pr.calendar_week_id = :week_id
                  AND pr.production_line_id IN :line_ids
                GROUP BY cw.week_label, it.issue_type_name
                ORDER BY it.issue_type_name
            """

        statement = text(sql).bindparams(bindparam("line_ids", expanding=True))
        return self._fetch_all(
            statement=statement,
            params={"week_id": week_id, "line_ids": line_ids},
        )

    def get_affected_lots(
        self, week_id: int, line_ids: list[int]
    ) -> list[dict[str, Any]]:
        if not line_ids:
            return []

        statement = text(
            """
            SELECT
              cw.week_label,
              pl.line_name,
              l.lot_code,
              COUNT(*)::integer AS issue_count,
              STRING_AGG(
                DISTINCT it.issue_type_name,
                ', '
                ORDER BY it.issue_type_name
              ) AS issue_types
            FROM production_issues pi
            JOIN production_runs pr ON pr.production_run_id = pi.production_run_id
            JOIN issue_types it ON it.issue_type_id = pi.issue_type_id
            JOIN calendar_weeks cw ON cw.calendar_week_id = pr.calendar_week_id
            JOIN production_lines pl ON pl.production_line_id = pr.production_line_id
            JOIN lots l ON l.lot_id = pr.lot_id
            WHERE pr.calendar_week_id = :week_id
              AND pr.production_line_id IN :line_ids
            GROUP BY cw.week_label, pl.line_name, l.lot_code
            ORDER BY issue_count DESC, l.lot_code
            """
        ).bindparams(bindparam("line_ids", expanding=True))
        return self._fetch_all(
            statement=statement,
            params={"week_id": week_id, "line_ids": line_ids},
        )

    def _fetch_all(
        self, statement: Any, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        with self._engine.begin() as connection:
            rows = connection.execute(statement, params).mappings().all()
        return [dict(row) for row in rows]
