-- db/seed.sql
-- Seed data for the Operations Analyst user story.
--
-- Purpose:
--   Insert a SMALL but representative dataset that exercises all Acceptance Criteria:
--   - multiple weeks
--   - multiple production lines
--   - multiple lots
--   - multiple issue types
--   - issues recorded through the single authoritative view `issue_occurrences`
--   - a few shipments to populate shipping tables (not required for ACs, but keeps schema realistic)
--
-- Idempotency:
--   This script is safe to re-run because it uses ON CONFLICT guards and
--   deterministic natural keys (week_label, line_name, lot_code, etc.).

BEGIN;

DO $$
DECLARE
  v_week_w03 BIGINT;
  v_week_w04 BIGINT;
  v_line_1 BIGINT;
  v_line_2 BIGINT;
  v_line_4 BIGINT;
  v_shift_day BIGINT;
  v_shift_night BIGINT;
  v_shift_swing BIGINT;

  v_part_sw BIGINT;
  v_part_hx BIGINT;
  v_part_br BIGINT;

  v_lot_1001 BIGINT;
  v_lot_1002 BIGINT;
  v_lot_2001 BIGINT;
  v_lot_2002 BIGINT;
  v_lot_3001 BIGINT;

  v_issue_material BIGINT;
  v_issue_changeover BIGINT;
  v_issue_tool BIGINT;
  v_issue_sensor BIGINT;
  v_issue_quality BIGINT;
  v_issue_training BIGINT;

  v_customer_acme BIGINT;
  v_customer_beta BIGINT;
  v_carrier_ups BIGINT;
  v_carrier_fedex BIGINT;
  v_so_58689 BIGINT;
  v_so_52588 BIGINT;

  v_run_id BIGINT;
BEGIN
  ---------------------------------------------------------------------------
  -- 1) Dimension/reference data
  ---------------------------------------------------------------------------

  -- Production lines
  INSERT INTO production_lines(line_name) VALUES
    ('Line 1'), ('Line 2'), ('Line 4')
  ON CONFLICT (line_name) DO NOTHING;

  SELECT production_line_id INTO v_line_1 FROM production_lines WHERE line_name = 'Line 1';
  SELECT production_line_id INTO v_line_2 FROM production_lines WHERE line_name = 'Line 2';
  SELECT production_line_id INTO v_line_4 FROM production_lines WHERE line_name = 'Line 4';

  -- Shifts (must match CHECK constraint: day/night/swing)
  INSERT INTO shifts(shift_name) VALUES
    ('day'), ('night'), ('swing')
  ON CONFLICT (shift_name) DO NOTHING;

  SELECT shift_id INTO v_shift_day FROM shifts WHERE shift_name = 'day';
  SELECT shift_id INTO v_shift_night FROM shifts WHERE shift_name = 'night';
  SELECT shift_id INTO v_shift_swing FROM shifts WHERE shift_name = 'swing';

  -- Calendar weeks
  INSERT INTO calendar_weeks(week_label, start_date, end_date) VALUES
    ('2026-W03', DATE '2026-01-12', DATE '2026-01-18'),
    ('2026-W04', DATE '2026-01-19', DATE '2026-01-25')
  ON CONFLICT (week_label) DO NOTHING;

  SELECT calendar_week_id INTO v_week_w03 FROM calendar_weeks WHERE week_label = '2026-W03';
  SELECT calendar_week_id INTO v_week_w04 FROM calendar_weeks WHERE week_label = '2026-W04';

  -- Issue types
  INSERT INTO issue_types(issue_type_name) VALUES
    ('material_shortage'),
    ('changeover_delay'),
    ('tool_wear'),
    ('sensor_fault'),
    ('quality_hold'),
    ('operator_training')
  ON CONFLICT (issue_type_name) DO NOTHING;

  SELECT issue_type_id INTO v_issue_material FROM issue_types WHERE issue_type_name = 'material_shortage';
  SELECT issue_type_id INTO v_issue_changeover FROM issue_types WHERE issue_type_name = 'changeover_delay';
  SELECT issue_type_id INTO v_issue_tool FROM issue_types WHERE issue_type_name = 'tool_wear';
  SELECT issue_type_id INTO v_issue_sensor FROM issue_types WHERE issue_type_name = 'sensor_fault';
  SELECT issue_type_id INTO v_issue_quality FROM issue_types WHERE issue_type_name = 'quality_hold';
  SELECT issue_type_id INTO v_issue_training FROM issue_types WHERE issue_type_name = 'operator_training';

  -- Parts
  INSERT INTO parts(part_number, description) VALUES
    ('SW-6899-B', 'Switch assembly'),
    ('HX-1010-A', 'Hydraulic housing'),
    ('BR-2222-C', 'Bracket')
  ON CONFLICT (part_number) DO UPDATE
    SET description = EXCLUDED.description;

  SELECT part_id INTO v_part_sw FROM parts WHERE part_number = 'SW-6899-B';
  SELECT part_id INTO v_part_hx FROM parts WHERE part_number = 'HX-1010-A';
  SELECT part_id INTO v_part_br FROM parts WHERE part_number = 'BR-2222-C';

  -- Lots
  INSERT INTO lots(lot_code, part_id, created_date) VALUES
    ('LOT-1001', v_part_sw, DATE '2026-01-10'),
    ('LOT-1002', v_part_sw, DATE '2026-01-11'),
    ('LOT-2001', v_part_hx, DATE '2026-01-10'),
    ('LOT-2002', v_part_hx, DATE '2026-01-18'),
    ('LOT-3001', v_part_br, DATE '2026-01-09')
  ON CONFLICT (lot_code) DO UPDATE
    SET part_id = EXCLUDED.part_id,
        created_date = EXCLUDED.created_date;

  SELECT lot_id INTO v_lot_1001 FROM lots WHERE lot_code = 'LOT-1001';
  SELECT lot_id INTO v_lot_1002 FROM lots WHERE lot_code = 'LOT-1002';
  SELECT lot_id INTO v_lot_2001 FROM lots WHERE lot_code = 'LOT-2001';
  SELECT lot_id INTO v_lot_2002 FROM lots WHERE lot_code = 'LOT-2002';
  SELECT lot_id INTO v_lot_3001 FROM lots WHERE lot_code = 'LOT-3001';

  -- Customers / carriers / sales orders
  INSERT INTO customers(customer_name) VALUES
    ('ACME Industrial'),
    ('Beta Manufacturing')
  ON CONFLICT (customer_name) DO NOTHING;

  SELECT customer_id INTO v_customer_acme FROM customers WHERE customer_name = 'ACME Industrial';
  SELECT customer_id INTO v_customer_beta FROM customers WHERE customer_name = 'Beta Manufacturing';

  INSERT INTO carriers(carrier_name) VALUES
    ('UPS'),
    ('FedEx')
  ON CONFLICT (carrier_name) DO NOTHING;

  SELECT carrier_id INTO v_carrier_ups FROM carriers WHERE carrier_name = 'UPS';
  SELECT carrier_id INTO v_carrier_fedex FROM carriers WHERE carrier_name = 'FedEx';

  INSERT INTO sales_orders(sales_order_number, customer_id) VALUES
    ('SO-58689', v_customer_acme),
    ('SO-52588', v_customer_beta)
  ON CONFLICT (sales_order_number) DO UPDATE
    SET customer_id = EXCLUDED.customer_id;

  SELECT sales_order_id INTO v_so_58689 FROM sales_orders WHERE sales_order_number = 'SO-58689';
  SELECT sales_order_id INTO v_so_52588 FROM sales_orders WHERE sales_order_number = 'SO-52588';

  ---------------------------------------------------------------------------
  -- 2) Production runs + issues
  -- NOTE: Production issues are recorded ONLY via production_issues and then
  -- consumed via the authoritative view issue_occurrences.
  ---------------------------------------------------------------------------

  -- Week 2026-W03
  INSERT INTO production_runs(
    run_date, calendar_week_id, shift_id, production_line_id, lot_id,
    units_planned, units_actual, downtime_minutes
  ) VALUES
    (DATE '2026-01-12', v_week_w03, v_shift_day,   v_line_1, v_lot_1001, 1000,  950, 30),
    (DATE '2026-01-13', v_week_w03, v_shift_night, v_line_1, v_lot_1002,  900,  850, 45),
    (DATE '2026-01-14', v_week_w03, v_shift_day,   v_line_2, v_lot_2001, 1100, 1100,  0),
    (DATE '2026-01-15', v_week_w03, v_shift_swing, v_line_4, v_lot_3001,  700,  680, 20)
  ON CONFLICT (run_date, shift_id, production_line_id, lot_id) DO NOTHING;

  -- Attach issues (one per run max) - uses upsert keyed by production_run_id
  SELECT production_run_id INTO v_run_id
  FROM production_runs
  WHERE run_date = DATE '2026-01-12' AND shift_id = v_shift_day AND production_line_id = v_line_1 AND lot_id = v_lot_1001;
  INSERT INTO production_issues(production_run_id, issue_type_id, supervisor_notes)
  VALUES (v_run_id, v_issue_tool, 'Tool wear observed; replaced cutting insert.')
  ON CONFLICT (production_run_id) DO UPDATE
    SET issue_type_id = EXCLUDED.issue_type_id,
        supervisor_notes = EXCLUDED.supervisor_notes;

  SELECT production_run_id INTO v_run_id
  FROM production_runs
  WHERE run_date = DATE '2026-01-13' AND shift_id = v_shift_night AND production_line_id = v_line_1 AND lot_id = v_lot_1002;
  INSERT INTO production_issues(production_run_id, issue_type_id, supervisor_notes)
  VALUES (v_run_id, v_issue_material, 'Material shortage; supplier late delivery.')
  ON CONFLICT (production_run_id) DO UPDATE
    SET issue_type_id = EXCLUDED.issue_type_id,
        supervisor_notes = EXCLUDED.supervisor_notes;

  SELECT production_run_id INTO v_run_id
  FROM production_runs
  WHERE run_date = DATE '2026-01-15' AND shift_id = v_shift_swing AND production_line_id = v_line_4 AND lot_id = v_lot_3001;
  INSERT INTO production_issues(production_run_id, issue_type_id, supervisor_notes)
  VALUES (v_run_id, v_issue_sensor, 'Sensor fault; recalibrated and restarted.')
  ON CONFLICT (production_run_id) DO UPDATE
    SET issue_type_id = EXCLUDED.issue_type_id,
        supervisor_notes = EXCLUDED.supervisor_notes;

  -- Week 2026-W04
  INSERT INTO production_runs(
    run_date, calendar_week_id, shift_id, production_line_id, lot_id,
    units_planned, units_actual, downtime_minutes
  ) VALUES
    (DATE '2026-01-19', v_week_w04, v_shift_day,   v_line_1, v_lot_1001, 1000,  970, 15),
    (DATE '2026-01-20', v_week_w04, v_shift_night, v_line_2, v_lot_2002,  800,  760, 40),
    (DATE '2026-01-21', v_week_w04, v_shift_day,   v_line_4, v_lot_3001,  650,  650,  0),
    (DATE '2026-01-22', v_week_w04, v_shift_day,   v_line_2, v_lot_2001, 1200, 1150, 25)
  ON CONFLICT (run_date, shift_id, production_line_id, lot_id) DO NOTHING;

  SELECT production_run_id INTO v_run_id
  FROM production_runs
  WHERE run_date = DATE '2026-01-19' AND shift_id = v_shift_day AND production_line_id = v_line_1 AND lot_id = v_lot_1001;
  INSERT INTO production_issues(production_run_id, issue_type_id, supervisor_notes)
  VALUES (v_run_id, v_issue_changeover, 'Changeover delay due to fixture adjustment.')
  ON CONFLICT (production_run_id) DO UPDATE
    SET issue_type_id = EXCLUDED.issue_type_id,
        supervisor_notes = EXCLUDED.supervisor_notes;

  SELECT production_run_id INTO v_run_id
  FROM production_runs
  WHERE run_date = DATE '2026-01-20' AND shift_id = v_shift_night AND production_line_id = v_line_2 AND lot_id = v_lot_2002;
  INSERT INTO production_issues(production_run_id, issue_type_id, supervisor_notes)
  VALUES (v_run_id, v_issue_training, 'Operator training needed on new work instruction.')
  ON CONFLICT (production_run_id) DO UPDATE
    SET issue_type_id = EXCLUDED.issue_type_id,
        supervisor_notes = EXCLUDED.supervisor_notes;

  SELECT production_run_id INTO v_run_id
  FROM production_runs
  WHERE run_date = DATE '2026-01-22' AND shift_id = v_shift_day AND production_line_id = v_line_2 AND lot_id = v_lot_2001;
  INSERT INTO production_issues(production_run_id, issue_type_id, supervisor_notes)
  VALUES (v_run_id, v_issue_quality, 'Quality hold; pending inspection results.')
  ON CONFLICT (production_run_id) DO UPDATE
    SET issue_type_id = EXCLUDED.issue_type_id,
        supervisor_notes = EXCLUDED.supervisor_notes;

  ---------------------------------------------------------------------------
  -- 3) Shipments (not required by ACs, but seeds the shipping tables)
  ---------------------------------------------------------------------------

  INSERT INTO shipments(
    ship_date, calendar_week_id, lot_id, sales_order_id, destination_state,
    carrier_id, bol_number, tracking_or_pro, qty_shipped, ship_status,
    hold_reason, shipping_notes
  )
  SELECT
    src.ship_date,
    src.calendar_week_id,
    src.lot_id,
    src.sales_order_id,
    src.destination_state,
    src.carrier_id,
    src.bol_number,
    src.tracking_or_pro,
    src.qty_shipped,
    src.ship_status,
    src.hold_reason,
    src.shipping_notes
  FROM (
    VALUES
      (DATE '2026-01-17', v_week_w03, v_lot_1001, v_so_58689, 'IN', v_carrier_ups,   'BOL-0001', '1Z999', 500, 'partial', NULL, 'First partial ship.'),
      (DATE '2026-01-18', v_week_w03, v_lot_1001, v_so_58689, 'IN', v_carrier_ups,   'BOL-0002', '1Z998', 450, 'shipped', NULL, 'Completed shipment.'),
      (DATE '2026-01-18', v_week_w03, v_lot_1002, v_so_52588, 'IL', NULL,            NULL,       NULL,      0, 'on_hold', 'Quality hold', 'Waiting for release.'),
      (DATE '2026-01-25', v_week_w04, v_lot_3001, v_so_52588, 'IN', v_carrier_fedex, 'BOL-0100', 'FDX123', 0, 'backordered', 'Customer requested delay', 'No inventory to ship.')
  ) AS src(
    ship_date,
    calendar_week_id,
    lot_id,
    sales_order_id,
    destination_state,
    carrier_id,
    bol_number,
    tracking_or_pro,
    qty_shipped,
    ship_status,
    hold_reason,
    shipping_notes
  )
  WHERE NOT EXISTS (
    SELECT 1
    FROM shipments s
    WHERE s.ship_date = src.ship_date
      AND s.lot_id = src.lot_id
      AND s.sales_order_id = src.sales_order_id
      AND COALESCE(s.bol_number, '') = COALESCE(src.bol_number, '')
      AND s.ship_status = src.ship_status
      AND s.qty_shipped = src.qty_shipped
  );

END $$;

COMMIT;
