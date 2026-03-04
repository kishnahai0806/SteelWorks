"""Service layer for operations metrics and CSV exports."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import Any, Protocol

from app.models import IssueFilterSelection


class OperationsDataSource(Protocol):
    """Repository contract used by the service layer."""

    def get_available_weeks(self) -> list[dict[str, Any]]: ...

    def get_available_lines(self) -> list[dict[str, Any]]: ...

    def get_issue_summary(
        self, week_id: int, line_ids: list[int], group_by_line: bool
    ) -> list[dict[str, Any]]: ...

    def get_affected_lots(
        self, week_id: int, line_ids: list[int]
    ) -> list[dict[str, Any]]: ...


class OperationsMetricsService:
    """Application service boundary for operations metrics use cases."""

    def __init__(self, repository: OperationsDataSource | None = None) -> None:
        self._repository = repository

        # Fallback data keeps unit tests independent of a running database.
        self._weeks: list[dict[str, int | str]] = [
            {"calendar_week_id": 1, "week_label": "2026-W03"},
            {"calendar_week_id": 2, "week_label": "2026-W04"},
        ]
        self._lines: list[dict[str, int | str | bool]] = [
            {"production_line_id": 1, "line_name": "Line 1", "is_active": True},
            {"production_line_id": 2, "line_name": "Line 2", "is_active": False},
            {"production_line_id": 3, "line_name": "Line 4", "is_active": True},
        ]
        self._issue_occurrences: list[dict[str, int | str]] = [
            {
                "calendar_week_id": 1,
                "week_label": "2026-W03",
                "production_line_id": 1,
                "line_name": "Line 1",
                "lot_code": "LOT-1001",
                "issue_type_name": "tool_wear",
            },
            {
                "calendar_week_id": 1,
                "week_label": "2026-W03",
                "production_line_id": 1,
                "line_name": "Line 1",
                "lot_code": "LOT-1002",
                "issue_type_name": "material_shortage",
            },
            {
                "calendar_week_id": 1,
                "week_label": "2026-W03",
                "production_line_id": 3,
                "line_name": "Line 4",
                "lot_code": "LOT-3001",
                "issue_type_name": "sensor_fault",
            },
            {
                "calendar_week_id": 2,
                "week_label": "2026-W04",
                "production_line_id": 1,
                "line_name": "Line 1",
                "lot_code": "LOT-1001",
                "issue_type_name": "changeover_delay",
            },
            {
                "calendar_week_id": 2,
                "week_label": "2026-W04",
                "production_line_id": 2,
                "line_name": "Line 2",
                "lot_code": "LOT-2002",
                "issue_type_name": "operator_training",
            },
            {
                "calendar_week_id": 2,
                "week_label": "2026-W04",
                "production_line_id": 2,
                "line_name": "Line 2",
                "lot_code": "LOT-2001",
                "issue_type_name": "quality_hold",
            },
        ]

    def normalize_line_ids(self, line_ids: list[int]) -> list[int]:
        """Normalize line IDs for deterministic query behavior."""
        return sorted(set(line_ids))

    def get_available_weeks(self) -> list[dict[str, Any]]:
        """Return selectable production weeks."""
        if self._repository is not None:
            return self._repository.get_available_weeks()
        return sorted(self._weeks, key=lambda week: int(week["calendar_week_id"]))

    def get_available_lines(self) -> list[dict[str, Any]]:
        """Return selectable active production lines."""
        if self._repository is not None:
            return self._repository.get_available_lines()
        active_lines = [line for line in self._lines if bool(line["is_active"])]
        return sorted(active_lines, key=lambda line: str(line["line_name"]))

    def get_issue_summary(
        self,
        selection: IssueFilterSelection,
        group_by_line: bool,
    ) -> list[dict[str, Any]]:
        """Return issue totals for the selected week and line scope."""
        normalized_line_ids = self.normalize_line_ids(selection.production_line_ids)
        if not normalized_line_ids:
            return []

        if self._repository is not None:
            return self._repository.get_issue_summary(
                week_id=selection.calendar_week_id,
                line_ids=normalized_line_ids,
                group_by_line=group_by_line,
            )

        filtered = self._filter_fallback_issue_rows(
            week_id=selection.calendar_week_id,
            line_ids=normalized_line_ids,
        )
        return self._summarize_fallback_issues(filtered, group_by_line=group_by_line)

    def get_affected_lots(
        self, selection: IssueFilterSelection
    ) -> list[dict[str, Any]]:
        """Return affected lots for the selected week and line scope."""
        normalized_line_ids = self.normalize_line_ids(selection.production_line_ids)
        if not normalized_line_ids:
            return []

        if self._repository is not None:
            return self._repository.get_affected_lots(
                week_id=selection.calendar_week_id,
                line_ids=normalized_line_ids,
            )

        filtered = self._filter_fallback_issue_rows(
            week_id=selection.calendar_week_id,
            line_ids=normalized_line_ids,
        )
        lot_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in filtered:
            key = (
                str(row["week_label"]),
                str(row["line_name"]),
                str(row["lot_code"]),
            )
            existing = lot_groups.get(key)
            if existing is None:
                existing = {
                    "week_label": key[0],
                    "line_name": key[1],
                    "lot_code": key[2],
                    "issue_count": 0,
                    "issue_types": set(),
                }
                lot_groups[key] = existing
            existing["issue_count"] = int(existing["issue_count"]) + 1
            existing["issue_types"].add(str(row["issue_type_name"]))

        lots: list[dict[str, Any]] = []
        for key in sorted(lot_groups):
            grouped = lot_groups[key]
            lots.append(
                {
                    "week_label": grouped["week_label"],
                    "line_name": grouped["line_name"],
                    "lot_code": grouped["lot_code"],
                    "issue_count": grouped["issue_count"],
                    "issue_types": ", ".join(sorted(grouped["issue_types"])),
                }
            )
        return lots

    def export_issue_summary_csv(
        self,
        selection: IssueFilterSelection,
        group_by_line: bool,
    ) -> bytes:
        """Export issue summary to CSV bytes for download."""
        rows = self.get_issue_summary(selection=selection, group_by_line=group_by_line)
        fieldnames = ["week_label"]
        if group_by_line:
            fieldnames.append("line_name")
        fieldnames.extend(["issue_type_name", "issue_count"])
        return self._to_csv_bytes(rows=rows, fieldnames=fieldnames)

    def export_affected_lots_csv(self, selection: IssueFilterSelection) -> bytes:
        """Export affected lots to CSV bytes for download."""
        rows = self.get_affected_lots(selection=selection)
        fieldnames = [
            "week_label",
            "line_name",
            "lot_code",
            "issue_count",
            "issue_types",
        ]
        return self._to_csv_bytes(rows=rows, fieldnames=fieldnames)

    def _filter_fallback_issue_rows(
        self, week_id: int, line_ids: list[int]
    ) -> list[dict[str, int | str]]:
        return [
            row
            for row in self._issue_occurrences
            if int(row["calendar_week_id"]) == week_id
            and int(row["production_line_id"]) in line_ids
        ]

    def _summarize_fallback_issues(
        self, rows: list[dict[str, int | str]], group_by_line: bool
    ) -> list[dict[str, Any]]:
        grouped_counts: defaultdict[tuple[str, ...], int] = defaultdict(int)
        for row in rows:
            if group_by_line:
                key: tuple[str, ...] = (
                    str(row["week_label"]),
                    str(row["line_name"]),
                    str(row["issue_type_name"]),
                )
            else:
                key = (str(row["week_label"]), str(row["issue_type_name"]))
            grouped_counts[key] += 1

        summary: list[dict[str, Any]] = []
        for key in sorted(grouped_counts):
            if group_by_line:
                summary.append(
                    {
                        "week_label": key[0],
                        "line_name": key[1],
                        "issue_type_name": key[2],
                        "issue_count": grouped_counts[key],
                    }
                )
            else:
                summary.append(
                    {
                        "week_label": key[0],
                        "issue_type_name": key[1],
                        "issue_count": grouped_counts[key],
                    }
                )
        return summary

    def _to_csv_bytes(self, rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
        return buffer.getvalue().encode("utf-8")
