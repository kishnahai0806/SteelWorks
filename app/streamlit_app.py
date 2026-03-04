"""Streamlit entrypoint for the operations issue metrics dashboard."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from app.models import IssueFilterSelection
from app.repository import OperationsRepository
from app.service import OperationsMetricsService


def _build_service(database_url: str) -> OperationsMetricsService:
    repository = OperationsRepository.from_database_url(database_url=database_url)
    return OperationsMetricsService(repository=repository)


@st.cache_resource(show_spinner=False)
def _cached_service(database_url: str) -> OperationsMetricsService:
    return _build_service(database_url=database_url)


def _resolve_database_url() -> str:
    load_dotenv(dotenv_path=".env", override=False)
    return os.getenv("DATABASE_URL", "").strip()


def _display_table(title: str, rows: list[dict[str, Any]], empty_message: str) -> None:
    st.subheader(title)
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info(empty_message)


def main() -> None:
    st.set_page_config(page_title="Operations Issue Metrics", layout="wide")
    st.title("Operations Issue Metrics")
    st.caption("Filter by week and production line to review issue trends.")

    database_url = _resolve_database_url()
    if not database_url:
        st.error("DATABASE_URL is not set. Add it to `.env` before starting the app.")
        return

    try:
        service = _cached_service(database_url=database_url)
    except Exception as exc:  # pragma: no cover - UI display path
        st.error(f"Unable to initialize database connection: {exc}")
        return

    try:
        weeks = service.get_available_weeks()
        lines = service.get_available_lines()
    except Exception as exc:  # pragma: no cover - UI display path
        st.error(f"Unable to load filter values: {exc}")
        return

    if not weeks:
        st.warning("No weeks found in the database.")
        return
    if not lines:
        st.warning("No active production lines found in the database.")
        return

    week_label_to_id = {
        str(week["week_label"]): int(week["calendar_week_id"]) for week in weeks
    }
    line_name_to_id = {
        str(line["line_name"]): int(line["production_line_id"]) for line in lines
    }

    selected_week_label = st.selectbox(
        "Week",
        options=list(week_label_to_id.keys()),
        index=0,
    )
    selected_line_names = st.multiselect(
        "Production lines",
        options=list(line_name_to_id.keys()),
        default=list(line_name_to_id.keys()),
    )
    group_by_line = st.checkbox("Group summary by line", value=True)

    selection = IssueFilterSelection(
        calendar_week_id=week_label_to_id[selected_week_label],
        production_line_ids=[line_name_to_id[name] for name in selected_line_names],
    )

    issue_summary = service.get_issue_summary(
        selection=selection, group_by_line=group_by_line
    )
    affected_lots = service.get_affected_lots(selection=selection)

    summary_total = sum(int(row["issue_count"]) for row in issue_summary)
    _display_table(
        title="Issue Summary",
        rows=issue_summary,
        empty_message="No issues found for the selected scope.",
    )
    st.write(f"Issue summary rows: {len(issue_summary)}")
    st.write(f"Total issues: {summary_total}")
    st.download_button(
        label="Download issue summary CSV",
        data=service.export_issue_summary_csv(
            selection=selection, group_by_line=group_by_line
        ),
        file_name="issue_summary.csv",
        mime="text/csv",
    )

    _display_table(
        title="Affected Lots",
        rows=affected_lots,
        empty_message="No affected lots found for the selected scope.",
    )
    st.write(f"Affected lots rows: {len(affected_lots)}")
    st.download_button(
        label="Download affected lots CSV",
        data=service.export_affected_lots_csv(selection=selection),
        file_name="affected_lots.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
