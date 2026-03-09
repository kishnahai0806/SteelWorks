"""Unit tests for operations service behavior without a real database."""

from __future__ import annotations

import logging

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


def test_get_issue_summary_uses_selection_scope() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1, 2, 3])
    summary = service.get_issue_summary(selection=selection, group_by_line=True)
    assert summary == [
        {
            "week_label": "2026-W03",
            "line_name": "Line 1",
            "issue_type_name": "material_shortage",
            "issue_count": 1,
        },
        {
            "week_label": "2026-W03",
            "line_name": "Line 1",
            "issue_type_name": "tool_wear",
            "issue_count": 1,
        },
        {
            "week_label": "2026-W03",
            "line_name": "Line 4",
            "issue_type_name": "sensor_fault",
            "issue_count": 1,
        },
    ]


def test_get_affected_lots_returns_lot_level_rows() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1])
    lots = service.get_affected_lots(selection=selection)
    assert lots == [
        {
            "week_label": "2026-W03",
            "line_name": "Line 1",
            "lot_code": "LOT-1001",
            "issue_count": 1,
            "issue_types": "tool_wear",
        },
        {
            "week_label": "2026-W03",
            "line_name": "Line 1",
            "lot_code": "LOT-1002",
            "issue_count": 1,
            "issue_types": "material_shortage",
        },
    ]


def test_export_issue_summary_csv_matches_display_scope() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1, 2])
    payload = service.export_issue_summary_csv(selection=selection, group_by_line=False)
    text = payload.decode("utf-8")
    assert "week_label,issue_type_name,issue_count" in text
    assert "2026-W03,material_shortage,1" in text
    assert "2026-W03,tool_wear,1" in text


def test_export_affected_lots_csv_matches_display_scope() -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[1, 2])
    payload = service.export_affected_lots_csv(selection=selection)
    text = payload.decode("utf-8")
    assert "week_label,line_name,lot_code,issue_count,issue_types" in text
    assert "2026-W03,Line 1,LOT-1001,1,tool_wear" in text


def test_get_issue_summary_logs_selected_scope(caplog) -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[3, 1])

    with caplog.at_level(logging.INFO):
        service.get_issue_summary(selection=selection, group_by_line=True)

    assert "Issue summary generated from fallback data" in caplog.text
    assert "week_id=1" in caplog.text
    assert "line_count=2" in caplog.text


def test_get_affected_lots_logs_when_no_lines_selected(caplog) -> None:
    service = OperationsMetricsService()
    selection = IssueFilterSelection(calendar_week_id=1, production_line_ids=[])

    with caplog.at_level(logging.INFO):
        rows = service.get_affected_lots(selection=selection)

    assert rows == []
    assert "Affected lots requested with no selected lines" in caplog.text
