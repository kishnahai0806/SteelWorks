# Operations Issue Metrics

Streamlit dashboard for weekly manufacturing issue metrics with:

- production week and line filters
- issue summary reporting
- affected lots reporting
- CSV exports
- unit, integration, and Playwright end-to-end tests

## Prerequisites

- Python 3.13
- Poetry
- Docker Desktop (running)

## Environment Files

- `.env` (production DB URL from Render):
  - `DATABASE_URL=postgresql+pg8000://...`
- `.env.test` (test DB URL):
  - `TEST_DATABASE_URL=postgresql+pg8000://devuser:devpass@127.0.0.1:5433/testdb`
  - `DATABASE_URL_TEST=...` is also accepted for slide compatibility.

Examples are included in `.env.example` and `.env.test.example`.

## Install

```bash
poetry install
poetry run playwright install
```

## Run Streamlit App

```bash
poetry run streamlit run streamlit_app.py
```

## Run Tests

Run everything (unit + integration + e2e):

```bash
poetry run pytest -q
```

Integration/e2e tests:

- use `TEST_DATABASE_URL` from `.env.test`
- automatically start local Docker Postgres (`postgres:18`) if URL is `127.0.0.1:5433/testdb`
- reset schema + seed data before tests

## Run Pre-commit

```bash
python -m pip install -r requirements-dev.txt
pre-commit run --all-files
```
