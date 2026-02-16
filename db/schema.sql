-- db/schema.sql
-- Physical data design for Production + Shipping logs (PostgreSQL)

BEGIN;

-- DEV ONLY: drop tables so the file can be re-run.
DROP TABLE IF EXISTS production_issues;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS production_runs;
DROP TABLE IF EXISTS sales_orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS carriers;
DROP TABLE IF EXISTS lots;
DROP TABLE IF EXISTS parts;
DROP TABLE IF EXISTS calendar_weeks;
DROP TABLE IF EXISTS shifts;
DROP TABLE IF EXISTS production_lines;
DROP TABLE IF EXISTS issue_types;

-- Reference / dimension tables
CREATE TABLE production_lines (
  production_line_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  line_name TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_production_lines_line_name UNIQUE (line_name)
);

CREATE TABLE shifts (
  shift_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  shift_name TEXT NOT NULL,
  CONSTRAINT ck_shifts_shift_name CHECK (shift_name IN ('day', 'night', 'swing')),
  CONSTRAINT uq_shifts_shift_name UNIQUE (shift_name)
);

CREATE TABLE calendar_weeks (
  calendar_week_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  week_label TEXT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  CONSTRAINT ck_calendar_weeks_date_order CHECK (start_date <= end_date),
  CONSTRAINT ck_calendar_weeks_week_label CHECK (week_label ~ '^[0-9]{4}-W[0-9]{2}$'),
  CONSTRAINT uq_calendar_weeks_week_label UNIQUE (week_label),
  CONSTRAINT uq_calendar_weeks_date_range UNIQUE (start_date, end_date)
);

CREATE TABLE parts (
  part_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  part_number TEXT NOT NULL,
  description TEXT,
  CONSTRAINT uq_parts_part_number UNIQUE (part_number)
);

CREATE TABLE lots (
  lot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  lot_code TEXT NOT NULL,
  part_id BIGINT NOT NULL,
  created_date DATE,
  CONSTRAINT uq_lots_lot_code UNIQUE (lot_code),
  CONSTRAINT fk_lots_part_id
    FOREIGN KEY (part_id)
    REFERENCES parts(part_id)
    ON DELETE RESTRICT
);

CREATE TABLE issue_types (
  issue_type_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  issue_type_name TEXT NOT NULL,
  CONSTRAINT uq_issue_types_name UNIQUE (issue_type_name)
);

CREATE TABLE customers (
  customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_name TEXT NOT NULL,
  CONSTRAINT uq_customers_name UNIQUE (customer_name)
);

CREATE TABLE carriers (
  carrier_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  carrier_name TEXT NOT NULL,
  CONSTRAINT uq_carriers_name UNIQUE (carrier_name)
);

CREATE TABLE sales_orders (
  sales_order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sales_order_number TEXT NOT NULL,
  customer_id BIGINT NOT NULL,
  CONSTRAINT uq_sales_orders_number UNIQUE (sales_order_number),
  CONSTRAINT fk_sales_orders_customer_id
    FOREIGN KEY (customer_id)
    REFERENCES customers(customer_id)
    ON DELETE RESTRICT
);

-- Fact / transaction tables
CREATE TABLE production_runs (
  production_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_date DATE NOT NULL,
  calendar_week_id BIGINT NOT NULL,
  shift_id BIGINT NOT NULL,
  production_line_id BIGINT NOT NULL,
  lot_id BIGINT NOT NULL,
  units_planned INTEGER NOT NULL,
  units_actual INTEGER NOT NULL,
  downtime_minutes INTEGER NOT NULL,

  CONSTRAINT ck_production_runs_units_planned_nonneg CHECK (units_planned >= 0),
  CONSTRAINT ck_production_runs_units_actual_nonneg CHECK (units_actual >= 0),
  CONSTRAINT ck_production_runs_downtime_nonneg CHECK (downtime_minutes >= 0),

  CONSTRAINT fk_production_runs_calendar_week_id
    FOREIGN KEY (calendar_week_id)
    REFERENCES calendar_weeks(calendar_week_id)
    ON DELETE RESTRICT,

  CONSTRAINT fk_production_runs_shift_id
    FOREIGN KEY (shift_id)
    REFERENCES shifts(shift_id)
    ON DELETE RESTRICT,

  CONSTRAINT fk_production_runs_production_line_id
    FOREIGN KEY (production_line_id)
    REFERENCES production_lines(production_line_id)
    ON DELETE RESTRICT,

  CONSTRAINT fk_production_runs_lot_id
    FOREIGN KEY (lot_id)
    REFERENCES lots(lot_id)
    ON DELETE RESTRICT,

  -- reasonable log-level de-dupe guard
  CONSTRAINT uq_production_runs_natural UNIQUE (run_date, shift_id, production_line_id, lot_id)
);

CREATE TABLE production_issues (
  production_issue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  production_run_id BIGINT NOT NULL,
  issue_type_id BIGINT NOT NULL,
  supervisor_notes TEXT,

  -- Each production run has at most one primary issue in the provided data.
  CONSTRAINT uq_production_issues_production_run_id UNIQUE (production_run_id),

  CONSTRAINT fk_production_issues_production_run_id
    FOREIGN KEY (production_run_id)
    REFERENCES production_runs(production_run_id)
    ON DELETE CASCADE,

  CONSTRAINT fk_production_issues_issue_type_id
    FOREIGN KEY (issue_type_id)
    REFERENCES issue_types(issue_type_id)
    ON DELETE RESTRICT
);

CREATE TABLE shipments (
  shipment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ship_date DATE NOT NULL,
  calendar_week_id BIGINT NOT NULL,
  lot_id BIGINT NOT NULL,
  sales_order_id BIGINT NOT NULL,
  destination_state CHAR(2) NOT NULL,
  carrier_id BIGINT,
  bol_number TEXT,
  tracking_or_pro TEXT,
  qty_shipped INTEGER NOT NULL,
  ship_status TEXT NOT NULL,
  hold_reason TEXT,
  shipping_notes TEXT,

  CONSTRAINT ck_shipments_qty_nonneg CHECK (qty_shipped >= 0),
  CONSTRAINT ck_shipments_destination_state_len CHECK (char_length(destination_state) = 2),
  CONSTRAINT ck_shipments_ship_status CHECK (ship_status IN ('shipped', 'partial', 'on_hold', 'backordered')),
  CONSTRAINT ck_shipments_backordered_qty CHECK (ship_status <> 'backordered' OR qty_shipped = 0),

  CONSTRAINT fk_shipments_calendar_week_id
    FOREIGN KEY (calendar_week_id)
    REFERENCES calendar_weeks(calendar_week_id)
    ON DELETE RESTRICT,

  CONSTRAINT fk_shipments_lot_id
    FOREIGN KEY (lot_id)
    REFERENCES lots(lot_id)
    ON DELETE RESTRICT,

  CONSTRAINT fk_shipments_sales_order_id
    FOREIGN KEY (sales_order_id)
    REFERENCES sales_orders(sales_order_id)
    ON DELETE RESTRICT,

  CONSTRAINT fk_shipments_carrier_id
    FOREIGN KEY (carrier_id)
    REFERENCES carriers(carrier_id)
    ON DELETE RESTRICT
);

-- Indexes to support common reporting & drill-down queries
CREATE INDEX idx_lots_part_id ON lots(part_id);

CREATE INDEX idx_production_runs_run_date ON production_runs(run_date);
CREATE INDEX idx_production_runs_line_date ON production_runs(production_line_id, run_date);
CREATE INDEX idx_production_runs_lot_id ON production_runs(lot_id);
CREATE INDEX idx_production_runs_week_id ON production_runs(calendar_week_id);

CREATE INDEX idx_shipments_ship_date ON shipments(ship_date);
CREATE INDEX idx_shipments_status ON shipments(ship_status);
CREATE INDEX idx_shipments_lot_id ON shipments(lot_id);
CREATE INDEX idx_shipments_sales_order_id ON shipments(sales_order_id);
CREATE INDEX idx_shipments_destination_state_date ON shipments(destination_state, ship_date);

-- Useful for "show me what's on hold" dashboards
CREATE INDEX idx_shipments_on_hold
  ON shipments(ship_date)
  WHERE ship_status = 'on_hold';

CREATE INDEX idx_sales_orders_customer_id ON sales_orders(customer_id);

COMMIT;
