# Self-Review: Phase 2

## Changes
- Added Budget model and repository
- Added budget CLI commands (set, get, report, delete)
- Added budget API endpoints (CRUD + report)
- Added CSV export functionality
- Added E2E tests for CLI
- Added tests for budget domain and service
- Fixed CSV import to skip invalid rows
- Fixed route ordering in FastAPI (specific before general)
- Fixed SRP violation (budgets table creation moved to BudgetRepository)

## Design Decisions
1. **Soft budget control**: Transactions allowed even if they exceed budget. Report shows [OVER] flag.
2. **Safe CSV import**: Invalid rows are skipped and logged, not crashing the entire import.
3. **Prefix ID matching**: CLI commands support partial ID for convenience.

## Bug Fixed
- FastAPI route `/budgets/report/{month}` returned 404 because general route `/budgets/{category}/{month}` was registered first. Fixed by reordering route declarations.

## Tests Added
- 14 budget tests (domain + service)
- 3 CLI E2E tests
- 7 CSV import tests
- 3 regression tests updated

## Checklist
- [x] All tests pass (40 passed)
- [x] mypy strict mode passes
- [x] ruff check passes
- [x] ruff format passes
- [x] README updated