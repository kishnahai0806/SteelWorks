"""
Streamlit entry point for the Operations Issue Metrics Dashboard.

What this module does:
- Renders filter controls for week and production line selection (AC1/AC2).
- Re-queries data whenever filters change (AC3).
- Shows summary and affected-lot outputs sourced from one authoritative view (AC4/AC5/AC6/AC7).
- Supports grouped/ungrouped summary modes (AC8) and grouped-total validation (AC9).
- Exports exactly what is displayed in the two result tables (AC10/AC11).

Complexity:
- UI rendering overhead is O(1) per widget plus DataFrame rendering costs.
- Data load costs are dominated by query result size O(r * c) per table.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.db import resolve_database_url
from app.service import (
    dataframe_to_csv_bytes,
    fetch_affected_lots,
    fetch_issue_summary,
    get_filter_options,
    validate_group_totals,
)


def _format_week_option(week_row: pd.Series) -> str:
    """
    Render a human-readable week label for selectbox display.

    Complexity:
    - Time: O(1) because it formats a fixed number of scalar values.
    - Space: O(1) for the output string.
    """
    # Include date bounds so analysts can confidently select the intended week.
    return (
        f"{week_row['week_label']} "
        f"({week_row['start_date']} to {week_row['end_date']})"
    )


def _ensure_non_empty_filters(weeks_df: pd.DataFrame, lines_df: pd.DataFrame) -> None:
    """
    Stop the app early if filter dimensions are missing.

    Complexity:
    - Time: O(1).
    - Space: O(1).
    """
    if weeks_df.empty:
        st.error("No calendar weeks were found. Load schema + seed data first.")
        st.stop()
    if lines_df.empty:
        st.error("No active production lines were found. Load schema + seed data first.")
        st.stop()


def main() -> None:
    """
    Render the full dashboard page.

    Complexity:
    - Time: Dominated by database result sizes O(r * c) across loaded tables.
    - Space: Dominated by in-memory DataFrames O(r * c).
    """
    st.set_page_config(
        page_title="Operations Issue Metrics Dashboard",
        layout="wide",
    )
    st.title("Operations Issue Metrics Dashboard")
    st.caption(
        "Metrics are computed only from the authoritative database view "
        "`issue_occurrences`."
    )

    with st.sidebar:
        st.header("Connection")
        # Password masking reduces accidental exposure during screen sharing.
        database_url_input = st.text_input(
            "DATABASE_URL",
            value="",
            type="password",
            help="Use your Render PostgreSQL URL, e.g. postgresql://.../?sslmode=require",
        )

    try:
        database_url = resolve_database_url(database_url_input)
    except ValueError as exc:
        st.info(str(exc))
        st.stop()

    # Load filter dimensions before rendering the selection widgets.
    weeks_df, lines_df = get_filter_options(database_url)
    _ensure_non_empty_filters(weeks_df, lines_df)

    with st.sidebar:
        st.header("Filters")

        # Build display strings and a reverse map to the canonical week ID.
        week_display_values = weeks_df.apply(_format_week_option, axis=1).tolist()
        week_lookup = {
            display_text: int(week_id)
            for display_text, week_id in zip(
                week_display_values,
                weeks_df["calendar_week_id"],
                strict=True,
            )
        }
        selected_week_display = st.selectbox(
            "Production Week",
            options=week_display_values,
            index=0,
        )
        selected_week_id = week_lookup[selected_week_display]

        line_name_to_id = {
            str(line_name): int(line_id)
            for line_name, line_id in zip(
                lines_df["line_name"],
                lines_df["production_line_id"],
                strict=True,
            )
        }
        all_line_names = list(line_name_to_id.keys())
        selected_line_names = st.multiselect(
            "Production Lines",
            options=all_line_names,
            default=all_line_names,
        )
        selected_line_ids = [line_name_to_id[line_name] for line_name in selected_line_names]

        grouping_mode = st.radio(
            "Summary Grouping",
            options=[
                "By production line and issue type",
                "By issue type only",
            ],
            index=0,
        )
        group_by_line = grouping_mode == "By production line and issue type"

    if not selected_line_ids:
        st.warning("Select at least one production line to view metrics.")
        st.stop()

    summary_df = fetch_issue_summary(
        database_url,
        selected_week_id,
        selected_line_ids,
        group_by_line=group_by_line,
    )
    affected_lots_df = fetch_affected_lots(database_url, selected_week_id, selected_line_ids)
    raw_total, grouped_total, totals_match = validate_group_totals(
        database_url,
        selected_week_id,
        selected_line_ids,
    )

    # Top-level metrics provide an at-a-glance check before table drill-down.
    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
    metric_col_1.metric("Total Issues (Raw)", raw_total)
    metric_col_2.metric("Total Issues (Grouped)", grouped_total)
    metric_col_3.metric("Affected Lots", int(affected_lots_df.shape[0]))

    if totals_match:
        st.success("AC9 check passed: grouped totals match ungrouped source rows.")
    else:
        st.error("AC9 check failed: grouped totals do not match ungrouped source rows.")

    st.subheader("Issue Summary")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download Issue Summary (CSV)",
        data=dataframe_to_csv_bytes(summary_df),
        file_name="issue_summary.csv",
        mime="text/csv",
    )

    st.subheader("Affected Lots")
    st.dataframe(affected_lots_df, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download Affected Lots (CSV)",
        data=dataframe_to_csv_bytes(affected_lots_df),
        file_name="affected_lots.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()

