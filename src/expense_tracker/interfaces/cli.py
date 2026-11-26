"""Command-line interface (interface #1)."""

import argparse
import logging
import sys
from datetime import date
from decimal import Decimal, InvalidOperation

from expense_tracker.application.service import ExpenseService
from expense_tracker.domain.exceptions import (
    ExpenseTrackerError,
    InvalidAmountError,
)
from expense_tracker.storage.sqlite_repo import (
    SQLiteTransactionRepository,
    get_db_path,
)
from expense_tracker.utils.csv_importer import import_csv_safely
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

    sub.add_parser("list", help="List all transactions")
    sub.add_parser("report", help="Report by category")

    imp_p = sub.add_parser("import", help="Import transactions from CSV")
    imp_p.add_argument("file", help="Path to CSV file")

    del_p = sub.add_parser("delete", help="Delete a transaction")
    del_p.add_argument("id", help="Transaction id")

    return parser


def main() -> None:
    """CLI entry point: wire dependencies and dispatch the command."""
    setup_logging()
    args = build_parser().parse_args()

    # Composition root: build the real service here.
    service = ExpenseService(SQLiteTransactionRepository(get_db_path()))

    try:
        if args.command == "add":
            _handle_add(service, args)
        elif args.command == "list":
            _handle_list(service)
        elif args.command == "report":
            _handle_report(service)
        elif args.command == "import":
            _handle_import(service, args)
        elif args.command == "delete":
            _handle_delete(service, args)
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


def _handle_list(service: ExpenseService) -> None:
    transactions = service.get_all_transactions()
    if not transactions:
        print("No transactions yet.")
        return
    for tx in transactions:
        kind = "IN" if tx.is_income else "OUT"
        print(f"{tx.id[:8]} | {tx.date} | {kind} | {tx.amount} | {tx.category}")


def _handle_report(service: ExpenseService) -> None:
    report = service.get_report_by_category()
    if not report:
        print("No expenses yet.")
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


def _handle_delete(service: ExpenseService, args: argparse.Namespace) -> None:
    service.delete_transaction(args.id)
    logger.info("Deleted transaction %s", args.id)
    print(f"Deleted transaction {args.id}")


if __name__ == "__main__":
    main()