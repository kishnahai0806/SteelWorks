"""
SQL query definitions for the Operations Issue Metrics Dashboard.

Design intent:
- Keep SQL text centralized and reviewable.
- Ensure all issue analytics read from `issue_occurrences`, which is the
  authoritative source required by AC5.

Complexity note:
- Importing this module is O(1) time / O(1) space because it only defines
  static strings.
"""

# Query A: available production weeks for AC1 filter selection.
WEEK_OPTIONS_SQL = """
SELECT
  calendar_week_id,
  week_label,
  start_date,
  end_date
FROM calendar_weeks
ORDER BY start_date;
"""

# Query B: available active production lines for AC2 multi-select.
LINE_OPTIONS_SQL = """
SELECT
  production_line_id,
  line_name
FROM production_lines
WHERE is_active = TRUE
ORDER BY line_name;
"""

# Query C: ungrouped summary (line + issue type) for AC3/AC4/AC8.
# IMPORTANT: Reads only from `issue_occurrences` (AC5).
ISSUE_SUMMARY_BY_LINE_SQL = """
SELECT
  io.week_label,
  io.line_name,
  io.issue_type_name,
  COUNT(*)::bigint AS issue_count
FROM issue_occurrences io
WHERE io.calendar_week_id = %s
  AND io.production_line_id = ANY(%s)
GROUP BY io.week_label, io.line_name, io.issue_type_name
ORDER BY io.line_name, issue_count DESC, io.issue_type_name;
"""

# Query D: grouped summary (issue type only) for AC8 grouping behavior.
# IMPORTANT: Reads only from `issue_occurrences` (AC5).
ISSUE_SUMMARY_GROUPED_SQL = """
SELECT
  io.week_label,
  io.issue_type_name,
  COUNT(*)::bigint AS issue_count
FROM issue_occurrences io
WHERE io.calendar_week_id = %s
  AND io.production_line_id = ANY(%s)
GROUP BY io.week_label, io.issue_type_name
ORDER BY issue_count DESC, io.issue_type_name;
"""

# Query E: affected lots output for AC6/AC7.
# IMPORTANT: Reads only from `issue_occurrences` (AC5).
AFFECTED_LOTS_SQL = """
SELECT
  io.week_label,
  io.line_name,
  io.lot_code,
  COUNT(*)::bigint AS issue_count,
  STRING_AGG(DISTINCT io.issue_type_name, ', ' ORDER BY io.issue_type_name) AS issue_types
FROM issue_occurrences io
WHERE io.calendar_week_id = %s
  AND io.production_line_id = ANY(%s)
GROUP BY io.week_label, io.line_name, io.lot_code
ORDER BY issue_count DESC, io.lot_code;
"""

# Query F: raw count from source data used to validate AC9 consistency.
RAW_ISSUE_TOTAL_SQL = """
SELECT
  COUNT(*)::bigint AS raw_issue_rows
FROM issue_occurrences io
WHERE io.calendar_week_id = %s
  AND io.production_line_id = ANY(%s);
"""

# Query G: grouped count (by issue type) used to validate AC9 consistency.
GROUPED_ISSUE_TOTAL_SQL = """
SELECT
  COALESCE(SUM(grouped.issue_count), 0)::bigint AS grouped_issue_rows
FROM (
  SELECT COUNT(*)::bigint AS issue_count
  FROM issue_occurrences io
  WHERE io.calendar_week_id = %s
    AND io.production_line_id = ANY(%s)
  GROUP BY io.issue_type_id
) grouped;
"""

