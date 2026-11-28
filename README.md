# Expense Tracker

A personal expense tracker application with CLI and Web API interfaces. Built with Python, FastAPI, and SQLite, following Clean Architecture principles.

## Features

- **Transaction Management**: Add, list, edit, and delete transactions.
- **Budgets**: Set monthly budgets per category with soft control (allows overspending with warnings).
- **Reporting**: Expense reports by category, budget reports with remaining/overspent status.
- **Date Filtering**: Filter transactions and reports by date range.
- **CSV Import/Export**: Import transactions from CSV (with safe skipping of invalid rows) and export to CSV.
- **Dual Interfaces**: 
  - Command-Line Interface (CLI) via `expense-cli`.
  - RESTful Web API via FastAPI (with interactive Swagger UI).

## Architecture

The project follows a layered architecture (Clean Architecture):

- `domain/`: Core business models (`Transaction`, `Budget`) and exceptions.
- `storage/`: Data persistence layer (SQLite repositories).
- `application/`: Service layer containing business logic.
- `interfaces/`: Entry points (CLI and FastAPI).
- `utils/`: Helper utilities (CSV import/export, logging).
- `tests/`: Comprehensive test suite (unit, integration, E2E).

## Usage

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `EXPENSE_DB_PATH` | `expenses.db` | Path to SQLite database file |
| `EXPENSE_LOG_DIR` | Home directory | Directory for log files |


## API Interface Examples

Start the API server:
```bash
uv run uvicorn expense_tracker.interfaces.api:app --reload

Open Swagger UI at http://localhost:8000/docs.

Create transaction:
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": "500", "category": "Food", "date": "2024-01-15", "is_income": false}'

Set budget:
curl -X POST http://localhost:8000/budgets \
  -H "Content-Type: application/json" \
  -d '{"category": "Food", "month": "2024-01", "limit": "1000"}'

### CLI Interface

```bash
# Add a transaction
uv run expense-cli add --amount 500 --category Food

# List transactions (with optional date filters)
uv run expense-cli list --from 2024-01-01 --to 2024-01-31

# Edit a transaction (supports partial ID matching)
uv run expense-cli edit <transaction_id> --amount 600

# Set a monthly budget
uv run expense-cli budget set --category Food --month 2024-01 --limit 1000

# Check budget status
uv run expense-cli budget get --category Food --month 2024-01

# Export to CSV
uv run expense-cli export output.csv --from 2024-01-01 --to 2024-01-31


## Profiling

**Command:** `uv run python profiling/profile_csv.py`

**Data size:** 50,000 rows, ~2.0 MB

**Results:**
- Total time: ~0.8 seconds
- Memory: O(1) during parsing (generator), ~5 MB for final list
- Hottest function: `Transaction.__post_init__` (validation)

**Conclusion:** Generator-based CSV import processes 50,000 rows efficiently. Memory stays low because we parse lazily with `yield`, and only materialize the list at the end for atomicity. No optimization needed.


## Limitations

- **Soft budget control**: Transactions are allowed even if they exceed the budget. The report shows `[OVER]` flag for categories where spending exceeds the limit.
- **Single currency**: The application uses one currency (no exchange rates).
- **No authentication**: API has no user authentication (suitable for personal use).
- **SQLite only**: No support for PostgreSQL or other databases (but architecture allows adding them).

## Course Topics Map

| Topic | Where used |
|---|---|
| **Object model and OOP** | `domain/models.py` — frozen dataclass, invariants in `__post_init__`, `__eq__`, `__hash__` |
| **Composition and polymorphism** | `storage/protocols.py` — Protocol for repositories, dependency injection in service |
| **Collections and protocols** | `utils/csv_importer.py` — generator for O(1) memory, context managers for DB connections |
| **Modules and packages** | `interfaces/cli.py` and `interfaces/api.py` — entry points, clear imports |
| **Environments and dependencies** | `pyproject.toml`, `uv.lock`, `.env.example` |
| **Typing and analysis** | All public functions annotated, mypy strict mode, ruff linter and formatter |
| **Errors and resources** | `domain/exceptions.py`, validation in models, context managers for DB |
| **Testing and debugging** | `tests/` — unit, integration, E2E, regression test for CSV import |
| **Logging** | `utils/logging_config.py`, logging in CLI and API, separate from stdout |
| **Profiling** | `profiling/profile_csv.py` — cProfile measurement with conclusion |
| **Git** | Tag v2.0.0, feature branch, PR #1, self-review in SELF_REVIEW.md |

## Bug Investigation

**Bug:** FastAPI route `/budgets/report/{month}` returned 404 instead of the budget report.

**Root cause:** The general route `/budgets/{category}/{month}` was registered before the specific route `/budgets/report/{month}`. FastAPI matched "report" as a category name and looked for a budget with category="report", which didn't exist.

**Fix:** Reordered route declarations so that specific routes (like `/budgets/report/{month}`) are registered before general routes (like `/budgets/{category}/{month}`).

**Regression test:** Added `test_cli_e2e_budget_workflow` to verify the correct route is matched.

## Object Lifecycles

- **Transaction**: создаётся в `ExpenseService.add_transaction()` → передаётся в `repository.add()` → сохраняется в SQLite. Объект immutable (frozen), передаётся by reference.
- **Budget**: создаётся в `ExpenseService.set_budget()` → передаётся в `budget_repository.add()`. При повторном вызове с теми же category+month заменяет старый (INSERT OR REPLACE).

### Example: References

```python
tx = service.add_transaction(amount=100, category="Food")
# tx.id = "abc123..."
# tx.amount = Decimal("100")

# Передаём в repository — объект не копируется
repository.add(tx)

# tx остаётся тем же объектом (immutable, безопасно)
assert tx.amount == Decimal("100")  # Нельзя изменить случайно