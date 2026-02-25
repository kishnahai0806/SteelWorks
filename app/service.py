"""
Service scaffolding for the operations analytics user story.

This module intentionally contains stubs for future implementation.
Only small unit-tested business rules are implemented.
"""

from __future__ import annotations

from app.models import IssueFilterSelection


class OperationsMetricsService:
    """
    Application service boundary for operations metrics use cases.
    """

    def __init__(self) -> None:
        """
        Initialize minimal in-memory reference data used by unit-tested rules.
        """
        self._weeks: list[dict[str, int | str]] = [
            {"calendar_week_id": 2, "week_label": "2026-W04"},
            {"calendar_week_id": 1, "week_label": "2026-W03"},
        ]
        self._lines: list[dict[str, int | str | bool]] = [
            {"production_line_id": 3, "line_name": "Line 4", "is_active": True},
            {"production_line_id": 1, "line_name": "Line 1", "is_active": True},
            {"production_line_id": 2, "line_name": "Line 2", "is_active": False},
        ]

    def normalize_line_ids(self, line_ids: list[int]) -> list[int]:
        """
        Normalize line IDs for deterministic query behavior.

        Implemented business logic:
        - removes duplicates
        - sorts ascending
        """
        return sorted(set(line_ids))

    def get_available_weeks(self) -> list[dict]:
        """
        Return selectable production weeks (AC1).
        """
        return sorted(self._weeks, key=lambda week: int(week["calendar_week_id"]))

    def get_available_lines(self) -> list[dict]:
        """
        Return selectable production lines (AC2).
        """
        active_lines = [line for line in self._lines if bool(line["is_active"])]
        return sorted(active_lines, key=lambda line: str(line["line_name"]))

    def get_issue_summary(
        self,
        selection: IssueFilterSelection,
        group_by_line: bool,
    ) -> list[dict]:
        """
        Return issue totals for selected scope (AC3, AC4, AC5, AC8, AC9).
        """
        raise NotImplementedError("Scaffold only: implement issue summary logic.")

    def get_affected_lots(self, selection: IssueFilterSelection) -> list[dict]:
        """
        Return affected lots for selected scope (AC6, AC7).
        """
        raise NotImplementedError("Scaffold only: implement affected lot logic.")

    def export_issue_summary_csv(
        self,
        selection: IssueFilterSelection,
        group_by_line: bool,
    ) -> bytes:
        """
        Export issue summary as CSV (AC10, AC11).
        """
        raise NotImplementedError(
            "Scaffold only: implement issue summary export logic."
        )

    def export_affected_lots_csv(self, selection: IssueFilterSelection) -> bytes:
        """
        Export affected lots as CSV (AC10, AC11).
        """
        raise NotImplementedError("Scaffold only: implement affected lot export logic.")
