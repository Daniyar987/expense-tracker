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