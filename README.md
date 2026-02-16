# Operations Issue Metrics Dashboard

A small PostgreSQL + Python dashboard that implements the **Operations Analyst** user story:

> As an operations analyst, I want to view consistent, reliable issue metrics by week and production line, and clearly see which lots are affected, so that I can respond quickly and confidently to leadership inquiries without rework or manual reconciliation.

This repo contains:

- **PostgreSQL physical schema**: `db/schema.sql`
- **Seed data**: `db/seed.sql`
- **Sample SQL queries**: `db/sample_queries.sql`
- **Streamlit app**: `app/main.py`
- **Automated tests (pytest)**: `tests/test_acceptance_criteria.py`

---

## Project description

The core idea is to make issue reporting **consistent** and **auditable**:

- All issue metrics come from a single authoritative source in the database: the **view** `issue_occurrences`.
- The UI filters by **production week** and **one or more production lines**.
- The UI shows:
  - an **Issue Summary** (counts by issue type, optionally grouped by line)
  - an **Affected Lots** list (each lot + issue count + issue types)
- Exports are generated from the same tables shown on-screen (so exported data matches the UI).

---

## Tech stack

- PostgreSQL (Render-managed)
- Python 3.10+
- Streamlit (UI)
- psycopg (Postgres driver)
- pandas (tables + CSV export)
- pytest (tests)

---

## How to run / build

### 1) Create a Render PostgreSQL instance

1. In Render, create a **PostgreSQL** service.
2. Copy the **External Database URL**.
   - It usually looks like: `postgresql://user:pass@host:5432/dbname?sslmode=require`

### 2) Apply schema + seed data

From your repo root:

```bash
# Export DATABASE_URL for your terminal session
export DATABASE_URL='postgresql://...your_render_url...?sslmode=require'

# Apply schema
psql "$DATABASE_URL" -f db/schema.sql

# Insert sample data
psql "$DATABASE_URL" -f db/seed.sql
```

> Windows PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://...your_render_url...?sslmode=require"
psql $env:DATABASE_URL -f db/schema.sql
psql $env:DATABASE_URL -f db/seed.sql
```

### 3) Run the Streamlit app

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the dashboard
streamlit run app/main.py
```

The app will open in your browser. Paste your `DATABASE_URL` in the sidebar if it isn't already in your environment.

---

## Usage examples

### Example: View issue totals for Week 2026-W03, Lines 1 + 4

1. Select **Production Week** = `2026-W03`.
2. Select **Production Lines** = `Line 1`, `Line 4`.
3. Confirm:
   - **Issue Summary** shows deterministic counts.
   - **Affected Lots** shows `lot_code`, `issue_count`, and `issue_types`.
4. Click:
   - **Download issue summary (CSV)**
   - **Download affected lots (CSV)**

### Example: Export from SQL directly (psql)

The `db/sample_queries.sql` file includes export-friendly queries and `\copy` examples.

---

## How to run tests

Tests validate the Acceptance Criteria against a real database.

### Local

```bash
export DATABASE_URL='postgresql://...your_render_url...?sslmode=require'
pytest -q
```

### GitHub Actions (optional)

This project includes a workflow that spins up a temporary Postgres container, applies `schema.sql` + `seed.sql`, then runs `pytest`.

---

## Acceptance Criteria coverage

- **AC1/AC2/AC3**: Week + multi-line filters in Streamlit sidebar; changing either triggers a rerun.
- **AC4**: Deterministic queries; repeated runs with the same parameters return identical results (tested).
- **AC5**: All issue metrics come from `issue_occurrences` view.
- **AC6/AC7**: Affected lots list shows `lot_code`, `issue_count`, `issue_types`.
- **AC8**: Filtering and optional grouping by line; no manual calculations.
- **AC9**: UI validation panel ensures grouped totals equal raw totals.
- **AC10/AC11**: CSV exports come directly from the displayed DataFrames.

---

## AI code review (potential issues / improvements)

This code is intentionally simple for an MVP, but here are the main things to watch:

1. **Secrets handling**
   - Don’t commit your Render `DATABASE_URL`.
   - Use `.env` locally and set env vars in Render.

2. **Connection pooling**
   - The app opens a new connection per query. For heavier usage, add a small pool (e.g., `psycopg_pool`) or caching.

3. **Very large datasets**
   - For large tables, consider pagination for the drill-down and add more indexes based on real query plans.

4. **Authorization**
   - This MVP assumes trusted internal access. If exposed publicly, add auth.

---

## Repo checklist (what to commit)

- `db/schema.sql`
- `db/seed.sql`
- `db/sample_queries.sql`
- `app/` (all Python files)
- `tests/`
- `requirements.txt`
- `README.md`
- `.github/workflows/ci.yml` (optional)

