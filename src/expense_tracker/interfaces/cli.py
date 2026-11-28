"""Command-line interface (interface #1)."""

import argparse
import logging
import sys
from datetime import date
from decimal import Decimal, InvalidOperation

from expense_tracker.application.service import ExpenseService
from expense_tracker.domain.models import Budget, Transaction
from expense_tracker.domain.exceptions import (
    ExpenseTrackerError,
    InvalidAmountError,
)
from expense_tracker.storage.sqlite_repo import (
    SQLiteTransactionRepository,
    get_db_path,
)
from expense_tracker.utils.csv_importer import import_csv_safely
from expense_tracker.utils.csv_exporter import export_transactions_to_csv
from expense_tracker.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="expense-cli", description="Personal expense tracker"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a transaction")
    add_p.add_argument("--amount", required=True, help="Amount, e.g. 500.50")
    add_p.add_argument("--category", required=True, help="Category name")
    add_p.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    add_p.add_argument("--income", action="store_true", help="Mark as income")

    list_p = sub.add_parser("list", help="List all transactions")
    list_p.add_argument("--from", dest="from_date", default=None, help="Start date (YYYY-MM-DD)")
    list_p.add_argument("--to", dest="to_date", default=None, help="End date (YYYY-MM-DD)")

    report_p = sub.add_parser("report", help="Report by category")
    report_p.add_argument("--from", dest="from_date", default=None, help="Start date (YYYY-MM-DD)")
    report_p.add_argument("--to", dest="to_date", default=None, help="End date (YYYY-MM-DD)")

    imp_p = sub.add_parser("import", help="Import transactions from CSV")
    imp_p.add_argument("file", help="Path to CSV file")

    exp_p = sub.add_parser("export", help="Export transactions to CSV")
    exp_p.add_argument("file", help="Path to output CSV file")
    exp_p.add_argument("--from", dest="from_date", default=None, help="Start date (YYYY-MM-DD)")
    exp_p.add_argument("--to", dest="to_date", default=None, help="End date (YYYY-MM-DD)")

    del_p = sub.add_parser("delete", help="Delete a transaction")
    del_p.add_argument("id", help="Transaction id")

    edit_p = sub.add_parser("edit", help="Edit an existing transaction")
    edit_p.add_argument("id", help="Transaction id")
    edit_p.add_argument("--amount", default=None, help="New amount")
    edit_p.add_argument("--category", default=None, help="New category")
    edit_p.add_argument("--date", default=None, help="New date (YYYY-MM-DD)")
    edit_p.add_argument("--income", action="store_true", default=None, help="Mark as income")

    budget_p = sub.add_parser("budget", help="Manage monthly budgets")
    budget_sub = budget_p.add_subparsers(dest="budget_command", required=True)

    budget_set_p = budget_sub.add_parser("set", help="Set a budget for a category")
    budget_set_p.add_argument("--category", required=True, help="Category name")
    budget_set_p.add_argument("--month", required=True, help="Month (YYYY-MM)")
    budget_set_p.add_argument("--limit", required=True, help="Budget limit")

    budget_get_p = budget_sub.add_parser("get", help="Get budget for a category")
    budget_get_p.add_argument("--category", required=True, help="Category name")
    budget_get_p.add_argument("--month", required=True, help="Month (YYYY-MM)")

    budget_report_p = budget_sub.add_parser("report", help="Budget report for a month")
    budget_report_p.add_argument("--month", required=True, help="Month (YYYY-MM)")

    return parser


def main() -> None:
    """CLI entry point: wire dependencies and dispatch the command."""
    setup_logging()
    args = build_parser().parse_args()

    # Composition root: build the real service here.
    from expense_tracker.storage.sqlite_repo import SQLiteBudgetRepository
    service = ExpenseService(
        SQLiteTransactionRepository(get_db_path()),
        SQLiteBudgetRepository(get_db_path()),
    )

    try:
        if args.command == "add":
            _handle_add(service, args)
        elif args.command == "list":
            _handle_list(service, args)
        elif args.command == "report":
            _handle_report(service, args)
        elif args.command == "import":
            _handle_import(service, args)
        elif args.command == "export":
            _handle_export(service, args)
        elif args.command == "delete":
            _handle_delete(service, args)
        elif args.command == "edit":
            _handle_edit(service, args)
        elif args.command == "budget":
            _handle_budget(service, args)
    except ExpenseTrackerError as exc:
        logger.error("Operation failed: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error")
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


def _handle_add(service: ExpenseService, args: argparse.Namespace) -> None:
    try:
        amount = Decimal(args.amount)
    except InvalidOperation as exc:
        raise InvalidAmountError(f"Invalid amount: {args.amount}") from exc
    tx_date = date.fromisoformat(args.date) if args.date else date.today()
    tx = service.add_transaction(
        amount=amount, category=args.category,
        transaction_date=tx_date, is_income=args.income,
    )
    logger.info("Added transaction %s", tx.id)
    print(f"Added: {tx.id[:8]} | {tx.amount} | {tx.category}")


def _handle_list(service: ExpenseService, args: argparse.Namespace) -> None:
    """List transactions, optionally filtered by date range."""
    from_date = date.fromisoformat(args.from_date) if args.from_date else None
    to_date = date.fromisoformat(args.to_date) if args.to_date else None
    transactions = service.get_transactions_by_date_range(from_date, to_date)
    if not transactions:
        print("No transactions found.")
        return
    for tx in transactions:
        kind = "IN" if tx.is_income else "OUT"
        print(f"{tx.id[:8]} | {tx.date} | {kind} | {tx.amount} | {tx.category}")


def _handle_report(service: ExpenseService, args: argparse.Namespace) -> None:
    """Show expense report by category, optionally filtered by date range."""
    from_date = date.fromisoformat(args.from_date) if args.from_date else None
    to_date = date.fromisoformat(args.to_date) if args.to_date else None
    transactions = service.get_transactions_by_date_range(from_date, to_date)
    
    report: dict[str, Decimal] = {}
    for tx in transactions:
        if not tx.is_income:
            report[tx.category] = report.get(tx.category, Decimal("0")) + tx.amount
    
    if not report:
        print("No expenses found.")
        return
    print("Expenses by category:")
    for category, total in sorted(report.items()):
        print(f"  {category}: {total}")


def _handle_import(service: ExpenseService, args: argparse.Namespace) -> None:
    with open(args.file, encoding="utf-8") as handle:
        transactions = import_csv_safely(handle)
    for tx in transactions:
        service.add_transaction(
            amount=tx.amount, category=tx.category,
            transaction_date=tx.date, is_income=tx.is_income,
        )
    logger.info("Imported %d transactions", len(transactions))
    print(f"Imported {len(transactions)} transactions.")


def _handle_export(service: ExpenseService, args: argparse.Namespace) -> None:
    """Export transactions to CSV file."""
    from_date = date.fromisoformat(args.from_date) if args.from_date else None
    to_date = date.fromisoformat(args.to_date) if args.to_date else None
    transactions = service.get_transactions_by_date_range(from_date, to_date)

    csv_content = export_transactions_to_csv(transactions)
    with open(args.file, "w", encoding="utf-8", newline="") as handle:
        handle.write(csv_content)

    logger.info("Exported %d transactions to %s", len(transactions), args.file)
    print(f"Exported {len(transactions)} transactions to {args.file}.")


def _handle_delete(service: ExpenseService, args: argparse.Namespace) -> None:
    """Delete a transaction by id (supports prefix matching)."""
    existing = service.get_transaction_by_id(args.id)
    if existing is None:
        all_txs = service.get_all_transactions()
        matches = [tx for tx in all_txs if tx.id.startswith(args.id)]
        if len(matches) > 1:
            print(f"Error: ambiguous transaction id '{args.id}' (matches {len(matches)} transactions)", file=sys.stderr)
        else:
            print(f"Error: transaction {args.id} not found", file=sys.stderr)
        sys.exit(1)

    service.delete_transaction(existing.id)
    logger.info("Deleted transaction %s", existing.id)
    print(f"Deleted transaction {existing.id[:8]}")


def _handle_edit(service: ExpenseService, args: argparse.Namespace) -> None:
    """Edit an existing transaction."""
    existing = service.get_transaction_by_id(args.id)
    if existing is None:
        # Check if ambiguous or not found
        all_txs = service.get_all_transactions()
        matches = [tx for tx in all_txs if tx.id.startswith(args.id)]
        if len(matches) > 1:
            print(f"Error: ambiguous transaction id '{args.id}' (matches {len(matches)} transactions)", file=sys.stderr)
        else:
            print(f"Error: transaction {args.id} not found", file=sys.stderr)
        sys.exit(1)

    try:
        amount = Decimal(args.amount) if args.amount else existing.amount
    except InvalidOperation as exc:
        raise InvalidAmountError(f"Invalid amount: {args.amount}") from exc

    category = args.category if args.category else existing.category
    tx_date = date.fromisoformat(args.date) if args.date else existing.date
    is_income = args.income if args.income is not None else existing.is_income

    updated = Transaction(
        id=existing.id,
        amount=amount,
        category=category,
        date=tx_date,
        is_income=is_income,
    )
    service.update_transaction(updated)
    logger.info("Updated transaction %s", updated.id)
    print(f"Updated: {updated.id[:8]} | {updated.amount} | {updated.category}")


def _handle_budget(service: ExpenseService, args: argparse.Namespace) -> None:
    """Dispatch budget subcommands."""
    if args.budget_command == "set":
        _handle_budget_set(service, args)
    elif args.budget_command == "get":
        _handle_budget_get(service, args)
    elif args.budget_command == "report":
        _handle_budget_report(service, args)


def _handle_budget_set(service: ExpenseService, args: argparse.Namespace) -> None:
    """Set a monthly budget for a category."""
    try:
        limit = Decimal(args.limit)
    except InvalidOperation as exc:
        raise InvalidAmountError(f"Invalid limit: {args.limit}") from exc

    budget = service.set_budget(args.category, args.month, limit)
    logger.info("Set budget %s for %s in %s", budget.limit, budget.category, budget.month)
    print(f"Budget set: {budget.category} | {budget.month} | {budget.limit}")


def _handle_budget_get(service: ExpenseService, args: argparse.Namespace) -> None:
    """Get budget for a specific category and month."""
    budget = service.get_budget(args.category, args.month)
    if budget is None:
        print(f"No budget set for {args.category} in {args.month}")
        return

    remaining = service.get_remaining_budget(args.category, args.month)
    if remaining is not None:
        spent = budget.limit - remaining
        print(f"Budget: {budget.category} | {budget.month} | {budget.limit}")
        
        print(f"Spent: {spent} | Remaining: {remaining}")
    else:
        print(f"Budget: {budget.category} | {budget.month} | {budget.limit}")


def _handle_budget_report(service: ExpenseService, args: argparse.Namespace) -> None:
    """Show budget report for all categories in a month."""
    report = service.get_budget_report(args.month)
    if not report:
        print(f"No budgets set for {args.month}")
        return

    print(f"Budget report for {args.month}:")
    for category, data in sorted(report.items()):
        status = "OK" if data["remaining"] >= 0 else "OVER"
        print(f"  {category}: budget={data['budget']}, spent={data['spent']}, remaining={data['remaining']} [{status}]")


if __name__ == "__main__":
    main()
