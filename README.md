# Operations Issue Metrics Dashboard

Implements the Operations Analyst user story:

> As an operations analyst, I want to view consistent, reliable issue metrics by week and production line, and clearly see which lots are affected, so that I can respond quickly and confidently to leadership inquiries without rework or manual reconciliation.

## Project Description

This project provides:

- A PostgreSQL schema in `db/schema.sql` with an authoritative analytics view: `issue_occurrences`.
- Seed data in `db/seed.sql` across multiple weeks, lines, lots, issue types, and shipment context.
- A Streamlit dashboard in `app/main.py` for filtering, grouping, and exporting issue metrics.
- Integration tests in `tests/test_acceptance_criteria.py` that validate AC1-AC11.

All issue metrics shown in UI and tests are derived from `issue_occurrences` to enforce a single source of truth.

## How To Run / Build

### 1) Prerequisites

- Python 3.10+ (tested with 3.13 locally and 3.11 in CI)
- A PostgreSQL database URL (Render recommended)

### 2) Configure database connection

Recommended (one-time local setup):

1. Create a `.env` file in the project root.
2. Set your real Render URL:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
```

The app, bootstrap script, and tests automatically read `.env`.

Alternative (temporary per-terminal session):

PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://user:password@host:5432/dbname?sslmode=require"
```

Bash:

```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname?sslmode=require"
```

### 3) Install dependencies

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

### 4) Apply schema + seed data to Render Postgres

```bash
python scripts/bootstrap_render_db.py
```

This applies, in order:

- `db/schema.sql`
- `db/seed.sql`

### 5) Run dashboard

```bash
streamlit run app/main.py
```

If `.env` and shell env are both missing, the app will stop and prompt you to set `DATABASE_URL`.

## Usage Examples

### Example 1: Filter and compare issue metrics

1. In the top filter row, choose `Production Week = 2026-W04`.
2. Select production lines `Line 1` and `Line 2`.
3. Keep grouping as `By production line and issue type`.
4. Confirm:
   - issue summary table updates,
   - affected lots table updates,
   - grouped and raw totals match.

### Example 2: Grouped reporting for leadership

1. Keep same week + lines.
2. Change grouping to `By issue type only`.
3. Compare totals against previous view; totals should remain consistent.

### Example 3: Export exactly what is on screen

1. Click `Download Issue Summary (CSV)`.
2. Click `Download Affected Lots (CSV)`.
3. Exported CSV files match the displayed tables row-for-row and column-for-column.

## How To Run Tests

Set `DATABASE_URL` (or `.env`) to a dedicated test database (tests rebuild schema):

```bash
pytest -q
```

What tests do:

- Re-apply `db/schema.sql` and `db/seed.sql` at session start.
- Validate AC1-AC11 against real DB results.

GitHub Actions CI is defined in `.github/workflows/ci.yml` and runs `pytest` against a temporary Postgres container.

## Acceptance Criteria Mapping

- AC1/AC2: Week and multi-line selectors in the main filter row.
- AC3: Changing selectors re-queries all result sets.
- AC4: Same selection returns identical deterministic results.
- AC5: All issue analytics SQL reads from `issue_occurrences`.
- AC6/AC7: Affected lots table includes `lot_code`, `issue_count`, `issue_types`.
- AC8: Summary supports grouped and ungrouped output modes.
- AC9: Grouped totals are validated against raw source counts.
- AC10/AC11: CSV exports are generated from the exact DataFrames displayed in UI.

## AI Code Review (Potential Issues)

1. Connection overhead:
   - Current implementation opens a new DB connection per query.
   - For higher load, introduce `psycopg_pool` and request-level connection reuse.

2. Large-data scaling:
   - Current tables render fully in memory/dataframe.
   - Add pagination and server-side LIMIT/OFFSET for large datasets.

3. Test safety:
   - Integration tests run `db/schema.sql`, which drops/recreates tables.
   - Always run tests against a dedicated non-production database.

4. Security hardening:
   - Dashboard currently assumes trusted internal users.
   - Add authentication and role checks before broader deployment.
