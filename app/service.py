"""
Service-layer helpers for Operations Issue Metrics.

Responsibilities:
- Fetch filter options (weeks and lines).
- Fetch issue summaries in grouped/ungrouped forms.
- Fetch affected lot details.
- Validate grouped totals versus raw source totals (AC9).
- Convert DataFrames to CSV bytes for download exports (AC10/AC11).

Complexity summary:
- Each database-backed function is dominated by query result size, typically
  O(r * c) time and O(r * c) space due to DataFrame materialization.
- CSV conversion is O(r * c) time / O(r * c) space for the output buffer.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from app.db import run_query
from app.queries import (
    AFFECTED_LOTS_SQL,
    GROUPED_ISSUE_TOTAL_SQL,
    ISSUE_SUMMARY_BY_LINE_SQL,
    ISSUE_SUMMARY_GROUPED_SQL,
    LINE_OPTIONS_SQL,
    RAW_ISSUE_TOTAL_SQL,
    WEEK_OPTIONS_SQL,
)


def _normalize_line_ids(line_ids: Iterable[int]) -> list[int]:
    """
    Normalize line-id iterables to a sorted, unique integer list.

    Why this helper exists:
    - Enforces deterministic query parameter order for reproducible outputs.
    - Removes accidental duplicates from multiselect UI state.

    Complexity:
    - Time: O(n log n) because of sorting after deduplication.
    - Space: O(n) for the intermediate set/list.
    """
    # Convert to integers and deduplicate to avoid over-counting from repeated IDs.
    unique_ids = {int(line_id) for line_id in line_ids}
    return sorted(unique_ids)


def get_filter_options(database_url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load selectable weeks and active production lines for the sidebar filters.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        Tuple `(weeks_df, lines_df)`.

    Complexity:
    - Time: O(w + l), where `w` is weeks row count and `l` is lines row count.
    - Space: O(w + l) for the two DataFrames.
    """
    weeks_df = run_query(database_url, WEEK_OPTIONS_SQL)
    lines_df = run_query(database_url, LINE_OPTIONS_SQL)
    return weeks_df, lines_df


def fetch_issue_summary(
    database_url: str,
    calendar_week_id: int,
    line_ids: Iterable[int],
    *,
    group_by_line: bool,
) -> pd.DataFrame:
    """
    Fetch issue summary table for the selected week and lines.

    Args:
        database_url: PostgreSQL connection string.
        calendar_week_id: Selected production week ID.
        line_ids: Selected production line IDs.
        group_by_line: If True, keep line dimension; otherwise group by issue type only.

    Returns:
        DataFrame with deterministic ordering suitable for display and export.

    Complexity:
    - Time: O(r * c) after SQL execution for DataFrame materialization.
    - Space: O(r * c) for result storage.
    """
    normalized_line_ids = _normalize_line_ids(line_ids)
    if not normalized_line_ids:
        # Return schema-correct empty output so UI/export logic remains stable.
        if group_by_line:
            return pd.DataFrame(
                columns=["week_label", "line_name", "issue_type_name", "issue_count"]
            )
        return pd.DataFrame(columns=["week_label", "issue_type_name", "issue_count"])

    sql = ISSUE_SUMMARY_BY_LINE_SQL if group_by_line else ISSUE_SUMMARY_GROUPED_SQL
    return run_query(database_url, sql, (calendar_week_id, normalized_line_ids))


def fetch_affected_lots(
    database_url: str,
    calendar_week_id: int,
    line_ids: Iterable[int],
) -> pd.DataFrame:
    """
    Fetch affected lots for the selected week and lines (AC6/AC7).

    Args:
        database_url: PostgreSQL connection string.
        calendar_week_id: Selected production week ID.
        line_ids: Selected production line IDs.

    Returns:
        DataFrame containing lot-level issue counts and issue type labels.

    Complexity:
    - Time: O(r * c) after SQL execution for DataFrame materialization.
    - Space: O(r * c) for result storage.
    """
    normalized_line_ids = _normalize_line_ids(line_ids)
    if not normalized_line_ids:
        return pd.DataFrame(
            columns=["week_label", "line_name", "lot_code", "issue_count", "issue_types"]
        )

    return run_query(database_url, AFFECTED_LOTS_SQL, (calendar_week_id, normalized_line_ids))


def validate_group_totals(
    database_url: str,
    calendar_week_id: int,
    line_ids: Iterable[int],
) -> tuple[int, int, bool]:
    """
    Validate AC9: grouped totals must match raw source totals.

    Args:
        database_url: PostgreSQL connection string.
        calendar_week_id: Selected production week ID.
        line_ids: Selected production line IDs.

    Returns:
        `(raw_issue_rows, grouped_issue_rows, totals_match)`.

    Complexity:
    - Time: O(r) in database aggregation terms; O(1) in Python post-processing.
    - Space: O(1) in Python because each query returns a single-row result.
    """
    normalized_line_ids = _normalize_line_ids(line_ids)
    if not normalized_line_ids:
        return 0, 0, True

    raw_df = run_query(database_url, RAW_ISSUE_TOTAL_SQL, (calendar_week_id, normalized_line_ids))
    grouped_df = run_query(
        database_url,
        GROUPED_ISSUE_TOTAL_SQL,
        (calendar_week_id, normalized_line_ids),
    )

    # Defensive conversions handle NULL/empty shapes safely.
    raw_total = int(raw_df.iloc[0]["raw_issue_rows"]) if not raw_df.empty else 0
    grouped_total = int(grouped_df.iloc[0]["grouped_issue_rows"]) if not grouped_df.empty else 0
    return raw_total, grouped_total, raw_total == grouped_total


def dataframe_to_csv_bytes(table_df: pd.DataFrame) -> bytes:
    """
    Convert a DataFrame to UTF-8 CSV bytes for `st.download_button`.

    Args:
        table_df: DataFrame currently displayed in the UI.

    Returns:
        UTF-8 encoded CSV bytes representing exactly the displayed rows/columns.

    Complexity:
    - Time: O(r * c) to format all cells.
    - Space: O(r * c) for the generated CSV string/bytes buffer.
    """
    # `index=False` ensures exports match visible table columns exactly.
    csv_text = table_df.to_csv(index=False)
    return csv_text.encode("utf-8")

