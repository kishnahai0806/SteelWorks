"""Integration tests against a real PostgreSQL test database."""

from __future__ import annotations

from app.models import IssueFilterSelection
from app.service import OperationsMetricsService


def _line_id_by_name(service: OperationsMetricsService, name: str) -> int:
    for line in service.get_available_lines():
        if str(line["line_name"]) == name:
            return int(line["production_line_id"])
    raise AssertionError(f"Line name not found: {name}")


def test_get_available_filters_from_database(
    db_service: OperationsMetricsService,
) -> None:
    weeks = db_service.get_available_weeks()
    lines = db_service.get_available_lines()

    assert [str(week["week_label"]) for week in weeks] == ["2026-W03", "2026-W04"]
    assert [str(line["line_name"]) for line in lines] == ["Line 1", "Line 2", "Line 4"]


def test_issue_summary_grouped_by_line_uses_selected_scope(
    db_service: OperationsMetricsService,
) -> None:
    line_1_id = _line_id_by_name(db_service, "Line 1")
    line_4_id = _line_id_by_name(db_service, "Line 4")
    selection = IssueFilterSelection(
        calendar_week_id=1,
        production_line_ids=[line_1_id, line_4_id],
    )

    summary = db_service.get_issue_summary(selection=selection, group_by_line=True)
    rows = {
        (str(row["line_name"]), str(row["issue_type_name"]), int(row["issue_count"]))
        for row in summary
    }
    assert rows == {
        ("Line 1", "material_shortage", 1),
        ("Line 1", "tool_wear", 1),
        ("Line 4", "sensor_fault", 1),
    }


def test_affected_lots_and_exports_match_database_scope(
    db_service: OperationsMetricsService,
) -> None:
    line_2_id = _line_id_by_name(db_service, "Line 2")
    selection = IssueFilterSelection(
        calendar_week_id=2, production_line_ids=[line_2_id]
    )

    affected_lots = db_service.get_affected_lots(selection=selection)
    lot_codes = {str(row["lot_code"]) for row in affected_lots}
    assert lot_codes == {"LOT-2001", "LOT-2002"}

    summary_csv = db_service.export_issue_summary_csv(
        selection=selection, group_by_line=False
    ).decode("utf-8")
    lots_csv = db_service.export_affected_lots_csv(selection=selection).decode("utf-8")

    assert "issue_type_name,issue_count" in summary_csv
    assert "operator_training,1" in summary_csv
    assert "quality_hold,1" in summary_csv
    assert "lot_code,issue_count,issue_types" in lots_csv
    assert "LOT-2001,1,quality_hold" in lots_csv
