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
