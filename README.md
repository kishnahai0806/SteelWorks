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

## Deploy on Render (Docker)

1. Push your latest code to GitHub.
2. In Render, click `New` -> `Web Service`.
3. Connect this repository and choose branch `main`.
4. Set `Language` to `Docker`.
5. Under `Environment Variables`, add:
   - `DATABASE_URL`
   - `SENTRY_DSN`
6. Click `Deploy Web Service`.
7. After deploy completes, open your Render URL:
   - `https://<your-service>.onrender.com/`

Notes:

- This project Docker image listens on Render's `PORT` environment variable.
- Keep `SENTRY_DSN` unquoted when entering it in Render.

## Uptime Monitoring (UptimeRobot)

Use Streamlit's built-in health endpoint for checks:

- `https://<your-service>.onrender.com/_stcore/health`

Setup steps:

1. Go to UptimeRobot and click `Start monitoring in 30 seconds`.
2. Sign in with GitHub.
3. Choose `HTTP/website monitoring`.
4. Paste your health endpoint URL.
5. Click `Create Monitor`.
6. Send a test email notification.
7. Click `Finish Setup`.
