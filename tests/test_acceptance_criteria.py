"""
Integration tests for Operations Analyst Acceptance Criteria (AC1-AC11).

Test strategy:
- Use a real PostgreSQL database pointed to by `DATABASE_URL`.
- Rebuild schema and seed data at session start for deterministic results.
- Assert each acceptance criterion through the same service layer used by UI.

Safety note:
- These tests execute `db/schema.sql`, which drops/recreates tables.
- Run against a dedicated assignment/test database, not production.

Complexity:
- Each test is dominated by SQL query costs and DataFrame materialization.
- Python-side comparison helpers are typically O(r log r) when sorting rows.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import psycopg
import pytest

from app.db import resolve_database_url
from app.queries import (
    AFFECTED_LOTS_SQL,
    GROUPED_ISSUE_TOTAL_SQL,
    ISSUE_SUMMARY_BY_LINE_SQL,
    ISSUE_SUMMARY_GROUPED_SQL,
    RAW_ISSUE_TOTAL_SQL,
)
from app.service import (
    dataframe_to_csv_bytes,
    fetch_affected_lots,
    fetch_issue_summary,
    get_filter_options,
    validate_group_totals,
)


def _read_text_file(file_path: Path) -> str:
    """
    Read a UTF-8 file into memory.

    Complexity:
    - Time: O(n) for n file bytes.
    - Space: O(n) for returned text.
    """
    return file_path.read_text(encoding="utf-8")


def _normalize_dataframe_for_compare(table_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize row ordering for deterministic DataFrame equality checks.

    Complexity:
    - Time: O(r log r) because sorting dominates for `r` rows.
    - Space: O(r * c) for the copied/sorted DataFrame.
    """
    if table_df.empty:
        return table_df.copy()

    # Sort by all columns to neutralize row-order differences across queries/drivers.
    sort_columns = list(table_df.columns)
    return table_df.sort_values(by=sort_columns).reset_index(drop=True)


def _preferred_scope(database_url: str) -> tuple[int, list[int], pd.DataFrame, pd.DataFrame]:
    """
    Select a deterministic week + line set with known seeded issue rows.

    Selection logic:
    - Prefer week label `2026-W04` from seed data.
    - Prefer line names `Line 1` and `Line 2` because both contain issues in W04.
    - Fall back to first available values if those labels are absent.

    Complexity:
    - Time: O(w + l), where `w` is week count and `l` is line count.
    - Space: O(w + l) for loaded filter DataFrames.
    """
    weeks_df, lines_df = get_filter_options(database_url)

    if "2026-W04" in set(weeks_df["week_label"]):
        week_id = int(
            weeks_df.loc[weeks_df["week_label"] == "2026-W04", "calendar_week_id"].iloc[0]
        )
    else:
        week_id = int(weeks_df["calendar_week_id"].iloc[0])

    line_name_to_id = {
        str(name): int(line_id)
        for name, line_id in zip(
            lines_df["line_name"],
            lines_df["production_line_id"],
            strict=True,
        )
    }

    selected_line_ids: list[int] = []
    for preferred_name in ("Line 1", "Line 2"):
        if preferred_name in line_name_to_id:
            selected_line_ids.append(line_name_to_id[preferred_name])

    if not selected_line_ids:
        selected_line_ids.append(int(lines_df["production_line_id"].iloc[0]))

    return week_id, selected_line_ids, weeks_df, lines_df


@pytest.fixture(scope="session")
def database_url() -> str:
    """
    Provide database URL from environment or skip the entire suite.

    Complexity:
    - Time: O(1)
    - Space: O(1)
    """
    try:
        # Shared resolver supports direct env var, `.env`, or explicit override.
        return resolve_database_url(None)
    except ValueError:
        pytest.skip("DATABASE_URL is not set; skipping integration tests.")


@pytest.fixture(scope="session", autouse=True)
def rebuild_schema_and_seed(database_url: str) -> None:
    """
    Rebuild schema and seed deterministic data once per test session.

    Resource management:
    - Connection and cursor use context managers, ensuring closure even on failures.

    Complexity:
    - Time: O(n) for SQL text size + database execution cost.
    - Space: O(n) for SQL strings in memory.
    """
    repo_root = Path(__file__).resolve().parents[1]
    schema_sql = _read_text_file(repo_root / "db" / "schema.sql")
    seed_sql = _read_text_file(repo_root / "db" / "seed.sql")

    # Autocommit is required because scripts contain BEGIN/COMMIT blocks.
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_sql)
            cursor.execute(seed_sql)


def test_ac1_and_ac2_selection_options(database_url: str) -> None:
    """
    AC1 + AC2: user can select a week and one or more production lines.
    """
    weeks_df, lines_df = get_filter_options(database_url)

    assert not weeks_df.empty
    assert not lines_df.empty
    assert weeks_df["calendar_week_id"].nunique() >= 2
    assert lines_df["production_line_id"].nunique() >= 2


def test_ac3_filter_changes_update_results_consistently(database_url: str) -> None:
    """
    AC3: changing week or line updates all result sets consistently.
    """
    week_id, selected_line_ids, weeks_df, lines_df = _preferred_scope(database_url)

    # Use first selected line for week-change checks.
    line_id = selected_line_ids[0]
    first_week_id = int(weeks_df["calendar_week_id"].iloc[0])
    second_week_id = (
        int(weeks_df["calendar_week_id"].iloc[1])
        if len(weeks_df) > 1
        else first_week_id
    )

    summary_first_week = fetch_issue_summary(
        database_url,
        first_week_id,
        [line_id],
        group_by_line=True,
    )
    affected_first_week = fetch_affected_lots(database_url, first_week_id, [line_id])
    summary_second_week = fetch_issue_summary(
        database_url,
        second_week_id,
        [line_id],
        group_by_line=True,
    )

    first_label = str(
        weeks_df.loc[weeks_df["calendar_week_id"] == first_week_id, "week_label"].iloc[0]
    )
    second_label = str(
        weeks_df.loc[weeks_df["calendar_week_id"] == second_week_id, "week_label"].iloc[0]
    )

    if not summary_first_week.empty:
        assert set(summary_first_week["week_label"]) == {first_label}
    if not affected_first_week.empty:
        assert set(affected_first_week["week_label"]) == {first_label}
    if not summary_second_week.empty:
        assert set(summary_second_week["week_label"]) == {second_label}

    if first_week_id != second_week_id:
        assert not summary_first_week.equals(summary_second_week)

    # If there are at least two lines, switching line selection should alter scope.
    if lines_df["production_line_id"].nunique() >= 2:
        alt_line_id = int(lines_df["production_line_id"].iloc[1])
        summary_alt_line = fetch_issue_summary(
            database_url,
            week_id,
            [alt_line_id],
            group_by_line=True,
        )
        if not summary_alt_line.empty:
            alt_line_name = str(
                lines_df.loc[
                    lines_df["production_line_id"] == alt_line_id,
                    "line_name",
                ].iloc[0]
            )
            assert set(summary_alt_line["line_name"]) == {alt_line_name}


def test_ac4_deterministic_results_for_same_selection(database_url: str) -> None:
    """
    AC4: same week + line selection yields identical totals on repeated reads.
    """
    week_id, selected_line_ids, _, _ = _preferred_scope(database_url)

    first_result = fetch_issue_summary(
        database_url,
        week_id,
        selected_line_ids,
        group_by_line=True,
    )
    second_result = fetch_issue_summary(
        database_url,
        week_id,
        selected_line_ids,
        group_by_line=True,
    )

    pdt.assert_frame_equal(
        _normalize_dataframe_for_compare(first_result),
        _normalize_dataframe_for_compare(second_result),
        check_dtype=False,
    )


def test_ac5_authoritative_source_is_single_view(database_url: str) -> None:
    """
    AC5: issue counts derive from the single authoritative source `issue_occurrences`.
    """
    week_id, selected_line_ids, _, _ = _preferred_scope(database_url)

    # Assert all issue-focused SQL definitions explicitly read from the view.
    issue_sql_texts = [
        ISSUE_SUMMARY_BY_LINE_SQL,
        ISSUE_SUMMARY_GROUPED_SQL,
        AFFECTED_LOTS_SQL,
        RAW_ISSUE_TOTAL_SQL,
        GROUPED_ISSUE_TOTAL_SQL,
    ]
    assert all("issue_occurrences" in sql_text for sql_text in issue_sql_texts)

    summary_df = fetch_issue_summary(
        database_url,
        week_id,
        selected_line_ids,
        group_by_line=True,
    )
    summary_total = int(summary_df["issue_count"].sum()) if not summary_df.empty else 0

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)::bigint
                FROM issue_occurrences io
                WHERE io.calendar_week_id = %s
                  AND io.production_line_id = ANY(%s);
                """,
                (week_id, selected_line_ids),
            )
            raw_total = int(cursor.fetchone()[0])

    assert summary_total == raw_total


def test_ac6_and_ac7_affected_lots_visibility(database_url: str) -> None:
    """
    AC6 + AC7: affected lots list is shown with issue count and issue type context.
    """
    week_id, selected_line_ids, _, _ = _preferred_scope(database_url)
    affected_df = fetch_affected_lots(database_url, week_id, selected_line_ids)

    assert not affected_df.empty
    expected_columns = {"week_label", "line_name", "lot_code", "issue_count", "issue_types"}
    assert expected_columns.issubset(set(affected_df.columns))
    assert (affected_df["issue_count"] > 0).all()
    assert affected_df["issue_types"].astype(str).str.len().gt(0).all()


def test_ac8_and_ac9_grouping_and_total_consistency(database_url: str) -> None:
    """
    AC8 + AC9: grouped and ungrouped outputs are supported and totals stay consistent.
    """
    week_id, selected_line_ids, _, _ = _preferred_scope(database_url)

    summary_by_line_df = fetch_issue_summary(
        database_url,
        week_id,
        selected_line_ids,
        group_by_line=True,
    )
    summary_grouped_df = fetch_issue_summary(
        database_url,
        week_id,
        selected_line_ids,
        group_by_line=False,
    )
    raw_total, grouped_total, totals_match = validate_group_totals(
        database_url,
        week_id,
        selected_line_ids,
    )

    assert "line_name" in summary_by_line_df.columns
    assert "line_name" not in summary_grouped_df.columns
    assert totals_match

    by_line_total = int(summary_by_line_df["issue_count"].sum()) if not summary_by_line_df.empty else 0
    grouped_view_total = (
        int(summary_grouped_df["issue_count"].sum()) if not summary_grouped_df.empty else 0
    )
    assert by_line_total == raw_total
    assert grouped_view_total == grouped_total


def test_ac10_and_ac11_export_matches_screen_data(database_url: str) -> None:
    """
    AC10 + AC11: CSV export is available and exactly matches visible DataFrame content.
    """
    week_id, selected_line_ids, _, _ = _preferred_scope(database_url)

    summary_df = fetch_issue_summary(
        database_url,
        week_id,
        selected_line_ids,
        group_by_line=True,
    )
    affected_df = fetch_affected_lots(database_url, week_id, selected_line_ids)

    summary_csv_bytes = dataframe_to_csv_bytes(summary_df)
    affected_csv_bytes = dataframe_to_csv_bytes(affected_df)

    summary_roundtrip = pd.read_csv(io.BytesIO(summary_csv_bytes))
    affected_roundtrip = pd.read_csv(io.BytesIO(affected_csv_bytes))

    pdt.assert_frame_equal(
        _normalize_dataframe_for_compare(summary_df),
        _normalize_dataframe_for_compare(summary_roundtrip),
        check_dtype=False,
    )
    pdt.assert_frame_equal(
        _normalize_dataframe_for_compare(affected_df),
        _normalize_dataframe_for_compare(affected_roundtrip),
        check_dtype=False,
    )
