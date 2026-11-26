# Expense Tracker

Personal finance application for tracking income and expenses with category-based reporting.

## Purpose

The application helps users:
- Record income and expense transactions
- Organize transactions by categories
- Import transactions from CSV files
- View reports aggregated by category
- Access data through both CLI and web API

## Core Workflows

1. Add transaction: `uv run expense-cli add --amount 500 --category Food`
2. List transactions: `uv run expense-cli list`
3. Generate report: `uv run expense-cli report`
4. Import from CSV: `uv run expense-cli import demo_data.csv`
5. Delete transaction: `uv run expense-cli delete <id>`

## Project Structure

```
expense_tracker/
  src/expense_tracker/
    domain/
      models.py       - Transaction dataclass (frozen, Decimal)
      exceptions.py   - Custom error types
    storage/
      protocols.py    - TransactionRepository Protocol
      sqlite_repo.py  - SQLite implementation
    application/
      service.py      - Business logic shared by CLI and API
    interfaces/
      cli.py          - Interface 1: argparse CLI
      api.py          - Interface 2: FastAPI web API
    utils/
      csv_importer.py - Generator-based CSV parsing
      logging_config.py
  tests/
    conftest.py
    test_domain.py
    test_service.py
    test_regression.py
    test_interfaces.py
  profiling/
    profile_csv.py
  demo_data.csv
  pyproject.toml
  uv.lock
```

## Setup and Launch

Prerequisites: Python 3.10+ and the `uv` package manager.

Install dependencies:

```bash
uv sync
```

Run the CLI:

```bash
uv run expense-cli --help
uv run expense-cli add --amount 500 --category Food
uv run expense-cli list
uv run expense-cli report
```

Run the web API:

```bash
uv run uvicorn expense_tracker.interfaces.api:app --reload
```

Then open http://localhost:8000/docs for interactive API documentation.

Run all tests:

```bash
uv run pytest
```

Run static checks:

```bash
uv run mypy src
uv run ruff check src tests
```

## Environment Variables

- `EXPENSE_DB_PATH` (default: `expenses.db`) - path to the SQLite database file.

No secrets are required. The database file is created automatically in the working directory.

## Examples

CLI example:

```bash
$ uv run expense-cli add --amount 1200 --category Food --date 2024-01-15
Added: a1b2c3d4 | 1200 | Food

$ uv run expense-cli add --amount 800 --category Food --date 2024-01-16
Added: e5f6g7h8 | 800 | Food

$ uv run expense-cli report
Expenses by category:
  Food: 2000
```

API example:

```bash
$ curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": "500", "category": "Transport", "is_income": false}'
```

CSV import example. Create `data.csv` with these columns:

```
amount,category,date,is_income
100,Food,2024-01-15,false
200,Transport,2024-01-16,false
```

Then run:

```bash
uv run expense-cli import data.csv
```

## Key Invariant

Amounts must be strictly positive and represented exactly. We use `Decimal` instead of `float` to avoid rounding errors (for example, `0.1 + 0.2` is not exactly `0.3` in floating point). The invariant is enforced in `Transaction.__post_init__` and tested in `tests/test_domain.py`.

## Limitations

- Single currency only (no exchange rates)
- No user authentication
- No recurring transactions
- No budget limits (can be added as an extension)
- SQLite is single-writer; not suitable for concurrent multi-user access

## Applying the Course Material

This section is the map of how course topics are used in the project.

**Object model and OOP.** `Transaction` is a `frozen=True` dataclass, which guarantees immutability after creation and prevents accidentally shared state. Invariants (positive amount, non-empty category) are validated in `__post_init__`. Equality is based on `id`, implemented through `__eq__` and `__hash__`. No mutable default arguments are used. Object lifecycle: a transaction is created in the service, passed to the repository, and returned to the caller. Reference example: the service holds a reference to the repository through the Protocol; multiple transactions can share the same category string without side effects because strings are immutable.

**Composition and polymorphism.** `ExpenseService` depends on the `TransactionRepository` Protocol, not on the concrete `SQLiteTransactionRepository`. This allows substituting real storage with in-memory storage in tests. Both CLI and API share the same service instance through the composition root in `main()`.

**Collections and protocols.** CSV import uses a generator (`yield`) for O(1) memory complexity during parsing, which is critical for large files. The `@contextmanager` decorator ensures DB connections are closed even on error. `TransactionRepository` is a Protocol (duck typing). Cost estimates: `add()` is O(1), `get_all()` is O(n), `get_by_category()` is O(n) scan, `get_report_by_category()` is O(n).

**Modules and packages.** Clean package structure under `src/expense_tracker/`. The entry point `expense-cli` is defined in `pyproject.toml` under `[project.scripts]`, so the app runs without editing `sys.path`. Importing the `api` module does not start the server because the service is created lazily.

**Environments and dependencies.** Managed via `uv`. `pyproject.toml` separates application dependencies (`fastapi`, `uvicorn`) from development dependencies (`pytest`, `mypy`, `ruff`, `httpx`). `uv.lock` ensures reproducible builds. The Python version is pinned to `>=3.10`.

**Typing and analysis.** Full type annotations on all public functions and models. Checked with `mypy --strict`. Formatted and linted with `ruff`. All configuration is stored in `pyproject.toml`. No exceptions to strict mode are needed.

**Errors and resources.** Custom exceptions (`InvalidAmountError`, `InvalidRowError`) provide meaningful messages. DB connections are closed via context managers even on error. The CLI returns a non-zero exit code (`sys.exit(1)`) on failure. CSV rows are validated before any write to the database.

**Testing and debugging.** `pytest` with fixtures in `conftest.py`. In-memory SQLite serves as a substitute for real storage. Unit tests cover domain invariants and service logic; integration tests cover the HTTP interface. `test_regression.py` documents a fixed bug: partial CSV import was not atomic; now the entire file is validated before any writes.

**Logging.** Configured via `logging_config.py` with `INFO` level. Logs are written to `expense_tracker.log` and to stderr, keeping CLI stdout clean for user-facing output. No sensitive data is logged.

**Profiling.** `profiling/profile_csv.py` measures parsing of 50,000 rows (1.67 MB). Result: generator-based import completes in 0.746 seconds. Conclusion: lazy evaluation is effective; the main cost is UUID generation, not parsing.

**Git.** Feature branch workflow. Documented self-review in the Pull Request (checklist: mypy passed, tests green, README updated). The final version is tagged as `v1.0.0`.

## Bug Investigation

**Bug.** When importing a CSV file with an invalid row in the middle, the valid rows before it were already saved to the database, breaking atomicity.

**Discovery.** While testing CSV import with a file containing a mix of valid and invalid rows, I noticed that after the import failed, the database still contained the valid rows from before the error.

**Fix.** Changed the import logic to parse the entire file first into a list (`import_csv_safely`), and only then save transactions to the repository. If any row fails validation, an exception is raised before any writes occur.

**Regression test.** `tests/test_regression.py::test_csv_import_is_atomic` verifies that after a failed import, the database remains empty.

## Profiling Results

Command:

```bash
uv run python profiling/profile_csv.py
```

Output:

```
=== PROFILING RESULTS ===
Data size: 50000 rows, 1.67 MB
Parsed transactions: 50000

1150444 function calls in 0.746 seconds

Ordered by: cumulative time
ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1    0.009    0.009    0.739    0.739 csv_importer.py:37(import_csv_safely)
 50001    0.133    0.000    0.730    0.000 csv_importer.py:12(parse_csv_transactions)
 50001    0.081    0.000    0.400    0.000 <string>:2(__init__)
 50000    0.034    0.000    0.268    0.000 models.py:23(<lambda>)
 50001    0.040    0.000    0.191    0.000 csv.py:174(__next__)
 50000    0.101    0.000    0.136    0.000 csv.py:142(__init__)
 50001    0.008    0.000    0.051    0.000 models.py:25(__post_init__)

=== CONCLUSION ===
Generator-based CSV import processes 50,000 rows efficiently.
Memory usage stays low because we parse lazily with yield,
and only materialize the list at the end for atomicity.
Bottleneck: UUID generation (0.4s), not parsing.
```

## Demo Data

A sample CSV file `demo_data.csv` is included in the repository with 6 transactions across 3 categories for quick testing.


