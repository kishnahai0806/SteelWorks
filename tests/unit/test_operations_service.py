"""
Unit test scaffolding for operations service behavior.

These tests are intentionally minimal stubs except for the first implemented test.
"""

from __future__ import annotations

import pytest

from app.models import IssueFilterSelection
from app.service import OperationsMetricsService


def test_normalize_line_ids_deduplicates_and_sorts() -> None:
    """
    First implemented unit test + business rule.
    """
    service = OperationsMetricsService()
    assert service.normalize_line_ids([4, 1, 4, 2, 1]) == [1, 2, 4]


def test_get_available_weeks_returns_selectable_values() -> None:
    service = OperationsMetricsService()
    weeks = service.get_available_weeks()
    assert weeks == [
        {"calendar_week_id": 1, "week_label": "2026-W03"},
        {"calendar_week_id": 2, "week_label": "2026-W04"},
    ]


def test_get_available_lines_returns_selectable_values() -> None:
    service = OperationsMetricsService()
    lines = service.get_available_lines()
    assert lines == [
        {"production_line_id": 1, "line_name": "Line 1", "is_active": True},
        {"production_line_id": 3, "line_name": "Line 4", "is_active": True},
    ]


@pytest.mark.skip(
    reason="Scaffold stub: implement when issue summary logic is implemented."
)
def test_get_issue_summary_uses_selection_scope() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1, 2])
    _ = service.get_issue_summary(selection=selection, group_by_line=True)


@pytest.mark.skip(
    reason="Scaffold stub: implement when affected lot logic is implemented."
)
def test_get_affected_lots_returns_lot_level_rows() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1])
    _ = service.get_affected_lots(selection=selection)


@pytest.mark.skip(reason="Scaffold stub: implement when export logic is implemented.")
def test_export_issue_summary_csv_matches_display_scope() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1, 2])
    _ = service.export_issue_summary_csv(selection=selection, group_by_line=False)


@pytest.mark.skip(reason="Scaffold stub: implement when export logic is implemented.")
def test_export_affected_lots_csv_matches_display_scope() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1, 2])
    _ = service.export_affected_lots_csv(selection=selection)
