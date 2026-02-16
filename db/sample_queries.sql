-- db/sample_queries.sql
-- Assumes data has been loaded into the tables created by db/schema.sql

-- 1) Weekly production summary by line (planned vs actual + downtime)
SELECT
  cw.week_label,
  pl.line_name,
  SUM(pr.units_planned) AS units_planned,
  SUM(pr.units_actual) AS units_actual,
  SUM(pr.downtime_minutes) AS downtime_minutes
FROM production_runs pr
JOIN production_lines pl ON pl.production_line_id = pr.production_line_id
LEFT JOIN calendar_weeks cw ON cw.calendar_week_id = pr.calendar_week_id
GROUP BY cw.week_label, pl.line_name
ORDER BY cw.week_label, pl.line_name;

-- 2) Top issue types in the last 30 days (relative to max run_date in table)
WITH bounds AS (
  SELECT (MAX(run_date) - INTERVAL '30 days')::date AS start_date
  FROM production_runs
)
SELECT
  it.issue_type_name,
  COUNT(*) AS issue_count
FROM production_issues pi
JOIN issue_types it ON it.issue_type_id = pi.issue_type_id
JOIN production_runs pr ON pr.production_run_id = pi.production_run_id
JOIN bounds b ON pr.run_date >= b.start_date
GROUP BY it.issue_type_name
ORDER BY issue_count DESC, it.issue_type_name;

-- 3) Lots that had a production issue AND have shipments currently on hold or backordered
SELECT
  l.lot_code,
  p.part_number,
  it.issue_type_name,
  s.ship_date,
  s.ship_status,
  s.hold_reason
FROM production_issues pi
JOIN production_runs pr ON pr.production_run_id = pi.production_run_id
JOIN lots l ON l.lot_id = pr.lot_id
JOIN parts p ON p.part_id = l.part_id
JOIN issue_types it ON it.issue_type_id = pi.issue_type_id
JOIN shipments s ON s.lot_id = l.lot_id
WHERE s.ship_status IN ('on_hold', 'backordered')
ORDER BY s.ship_date DESC, l.lot_code;

-- 4) Shipped quantity by customer and week
SELECT
  cw.week_label,
  c.customer_name,
  SUM(s.qty_shipped) AS qty_shipped
FROM shipments s
JOIN sales_orders so ON so.sales_order_id = s.sales_order_id
JOIN customers c ON c.customer_id = so.customer_id
LEFT JOIN calendar_weeks cw ON cw.calendar_week_id = s.calendar_week_id
WHERE s.ship_status IN ('shipped', 'partial')
GROUP BY cw.week_label, c.customer_name
ORDER BY cw.week_label, qty_shipped DESC;

-- 5) Shipments currently on hold (with customer + carrier)
SELECT
  s.ship_date,
  so.sales_order_number,
  c.customer_name,
  l.lot_code,
  s.destination_state,
  ca.carrier_name,
  s.hold_reason,
  s.shipping_notes
FROM shipments s
JOIN sales_orders so ON so.sales_order_id = s.sales_order_id
JOIN customers c ON c.customer_id = so.customer_id
JOIN lots l ON l.lot_id = s.lot_id
LEFT JOIN carriers ca ON ca.carrier_id = s.carrier_id
WHERE s.ship_status = 'on_hold'
ORDER BY s.ship_date DESC, c.customer_name;

-- 6) Average downtime by line + shift
SELECT
  pl.line_name,
  sh.shift_name,
  AVG(pr.downtime_minutes)::numeric(10,2) AS avg_downtime_minutes,
  COUNT(*) AS run_count
FROM production_runs pr
JOIN production_lines pl ON pl.production_line_id = pr.production_line_id
JOIN shifts sh ON sh.shift_id = pr.shift_id
GROUP BY pl.line_name, sh.shift_name
ORDER BY pl.line_name, sh.shift_name;

-- 7) Daily production variance (planned - actual)
SELECT
  pr.run_date,
  SUM(pr.units_planned - pr.units_actual) AS total_variance
FROM production_runs pr
GROUP BY pr.run_date
ORDER BY pr.run_date;

-- 8) Shipments for a specific sales order number (edit the literal)
SELECT
  s.ship_date,
  l.lot_code,
  s.qty_shipped,
  s.ship_status,
  s.tracking_or_pro,
  s.bol_number,
  s.hold_reason,
  s.shipping_notes
FROM shipments s
JOIN sales_orders so ON so.sales_order_id = s.sales_order_id
JOIN lots l ON l.lot_id = s.lot_id
WHERE so.sales_order_number = 'SO-58689'
ORDER BY s.ship_date, s.shipment_id;

-- 9) Lead time (days) from first production run to first ship date per lot
WITH prod AS (
  SELECT lot_id, MIN(run_date) AS first_run_date
  FROM production_runs
  GROUP BY lot_id
), ship AS (
  SELECT lot_id, MIN(ship_date) AS first_ship_date
  FROM shipments
  GROUP BY lot_id
)
SELECT
  l.lot_code,
  p.part_number,
  prod.first_run_date,
  ship.first_ship_date,
  (ship.first_ship_date - prod.first_run_date) AS lead_time_days
FROM prod
JOIN ship ON ship.lot_id = prod.lot_id
JOIN lots l ON l.lot_id = prod.lot_id
JOIN parts p ON p.part_id = l.part_id
ORDER BY lead_time_days DESC, l.lot_code;

-- 10) Lots with multiple partial shipments (split shipments)
SELECT
  l.lot_code,
  so.sales_order_number,
  COUNT(*) AS partial_shipments,
  SUM(s.qty_shipped) AS total_qty_shipped
FROM shipments s
JOIN lots l ON l.lot_id = s.lot_id
JOIN sales_orders so ON so.sales_order_id = s.sales_order_id
WHERE s.ship_status = 'partial'
GROUP BY l.lot_code, so.sales_order_number
HAVING COUNT(*) >= 2
ORDER BY partial_shipments DESC, l.lot_code;

-- =====================================================================
-- AC-driven queries for the Operations Analyst user story
-- =====================================================================

-- 11) (AC1/AC2/AC3) Available filter values (weeks + lines)
SELECT calendar_week_id, week_label, start_date, end_date
FROM calendar_weeks
ORDER BY start_date;

SELECT production_line_id, line_name
FROM production_lines
WHERE is_active = TRUE
ORDER BY line_name;

-- 12) (AC4/AC5) Authoritative issue totals for a selected week + selected lines
-- Replace :week_id and :line_ids as needed.
-- Example psql variables:
--   \set week_id 1
--   \set line_ids '{1,2}'
SELECT
  cw.week_label,
  pl.line_name,
  io.issue_type_name,
  COUNT(*) AS issue_count
FROM issue_occurrences io
JOIN calendar_weeks cw ON cw.calendar_week_id = io.calendar_week_id
JOIN production_lines pl ON pl.production_line_id = io.production_line_id
WHERE io.calendar_week_id = :week_id
  AND io.production_line_id = ANY(:line_ids::bigint[])
GROUP BY cw.week_label, pl.line_name, io.issue_type_name
ORDER BY pl.line_name, issue_count DESC, io.issue_type_name;

-- 13) (AC6/AC7) Affected lots list for the selected week + selected lines
-- Shows each affected lot with its issue type(s) and total issue count.
SELECT
  cw.week_label,
  pl.line_name,
  l.lot_code,
  COUNT(*) AS issue_count,
  STRING_AGG(DISTINCT io.issue_type_name, ', ' ORDER BY io.issue_type_name) AS issue_types
FROM issue_occurrences io
JOIN calendar_weeks cw ON cw.calendar_week_id = io.calendar_week_id
JOIN production_lines pl ON pl.production_line_id = io.production_line_id
JOIN lots l ON l.lot_id = io.lot_id
WHERE io.calendar_week_id = :week_id
  AND io.production_line_id = ANY(:line_ids::bigint[])
GROUP BY cw.week_label, pl.line_name, l.lot_code
ORDER BY issue_count DESC, l.lot_code;

-- 14) (AC9) Proof that grouped totals match ungrouped source data
-- The grouped sum must equal the raw count from the authoritative source.
WITH raw AS (
  SELECT COUNT(*) AS raw_issue_rows
  FROM issue_occurrences io
  WHERE io.calendar_week_id = :week_id
    AND io.production_line_id = ANY(:line_ids::bigint[])
), grouped AS (
  SELECT SUM(issue_count) AS grouped_issue_rows
  FROM (
    SELECT COUNT(*) AS issue_count
    FROM issue_occurrences io
    WHERE io.calendar_week_id = :week_id
      AND io.production_line_id = ANY(:line_ids::bigint[])
    GROUP BY io.issue_type_id
  ) x
)
SELECT
  raw.raw_issue_rows,
  grouped.grouped_issue_rows,
  (raw.raw_issue_rows = grouped.grouped_issue_rows) AS totals_match
FROM raw, grouped;

-- 15) (AC10/AC11) Export helper: same data as Query 12 but in a flat export-friendly shape
-- Use psql \copy to export exactly what is shown:
--   \copy ( <query below> ) TO 'issue_summary.csv' CSV HEADER
SELECT
  cw.week_label,
  pl.line_name,
  io.issue_type_name,
  COUNT(*) AS issue_count
FROM issue_occurrences io
JOIN calendar_weeks cw ON cw.calendar_week_id = io.calendar_week_id
JOIN production_lines pl ON pl.production_line_id = io.production_line_id
WHERE io.calendar_week_id = :week_id
  AND io.production_line_id = ANY(:line_ids::bigint[])
GROUP BY cw.week_label, pl.line_name, io.issue_type_name
ORDER BY cw.week_label, pl.line_name, io.issue_type_name;
