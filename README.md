# Operations Issue Metrics (Develop Scaffold)

This `develop` branch contains only minimal scaffolding for the operations user story:

- `app/models.py`: domain selection model (`IssueFilterSelection`)
- `app/service.py`: service class with function stubs
- `tests/unit/test_operations_service.py`: unit test stubs

Implemented now:

- First unit test: `test_normalize_line_ids_deduplicates_and_sorts`
- Related business logic: `OperationsMetricsService.normalize_line_ids`

All other tests are explicit stubs (`@pytest.mark.skip`) and no integration tests are included.

## Run unit tests

```bash
python -m pytest -q
```

## Developer quality checks

Install dev tooling:

```bash
python -m pip install -r requirements-dev.txt
```

Run formatter:

```bash
python -m ruff format app tests
```

Run linter:

```bash
python -m ruff check .
```

Run static type checker:

```bash
python -m mypy
```

Run tests with coverage:

```bash
python -m pytest --cov=app --cov-report=term-missing -q
```

## Pre-commit checks

Install git hooks:

```bash
python -m pip install -r requirements-dev.txt
pre-commit install
```

Run all pre-commit checks manually:

```bash
pre-commit run --all-files
```

Checks include:

- `ruff format`
- `ruff check`
- `mypy`
- unit tests (`pytest -q tests/unit`)

GitHub Actions runs the same pre-commit checks on pull request create/update.
