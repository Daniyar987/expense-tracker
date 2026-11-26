"""Application service: the business logic shared by CLI and API."""

from datetime import date
from decimal import Decimal

from expense_tracker.domain.models import Transaction
from expense_tracker.storage.protocols import TransactionRepository


class ExpenseService:
    """Expense tracking workflows on top of a repository.

    Depends on the TransactionRepository protocol, not on SQLite.
    """

    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    def add_transaction(
        self,
        amount: Decimal,
        category: str,
        transaction_date: date,
        is_income: bool,
    ) -> Transaction:
        """Create a transaction and persist it."""
        transaction = Transaction(
            amount=amount,
            category=category,
            date=transaction_date,
            is_income=is_income,
        )
        self._repository.add(transaction)
        return transaction

    def get_all_transactions(self) -> list[Transaction]:
        """Return all transactions."""
        return self._repository.get_all()

    def get_report_by_category(self) -> dict[str, Decimal]:
        """Sum expenses per category (income is excluded)."""
        report: dict[str, Decimal] = {}
        for tx in self._repository.get_all():
            if not tx.is_income:
                report[tx.category] = (
                    report.get(tx.category, Decimal("0")) + tx.amount
                )
        return report

    def delete_transaction(self, transaction_id: str) -> None:
        """Delete a transaction by id."""
        self._repository.delete(transaction_id)