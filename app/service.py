"""
Service scaffolding for the operations analytics user story.

This module intentionally contains stubs for future implementation.
Only the first unit-tested business rule is implemented.
"""

from __future__ import annotations

from app.models import IssueFilterSelection


class OperationsMetricsService:
    """
    Application service boundary for operations metrics use cases.
    """

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
        raise NotImplementedError("Scaffold only: implement week retrieval logic.")

    def get_available_lines(self) -> list[dict]:
        """
        Return selectable production lines (AC2).
        """
        raise NotImplementedError("Scaffold only: implement line retrieval logic.")

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
