"""Application service: the business logic shared by CLI and API."""

from datetime import date
from decimal import Decimal

from expense_tracker.domain.models import Budget, Transaction
from expense_tracker.storage.protocols import BudgetRepository, TransactionRepository


class ExpenseService:
    """Expense tracking workflows on top of a repository.

    Depends on the TransactionRepository protocol, not on SQLite.
    """

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        budget_repository: BudgetRepository,
    ) -> None:
        """Initialize the service with repositories."""
        self._transaction_repository = transaction_repository
        self._budget_repository = budget_repository

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
        self._transaction_repository.add(transaction)
        return transaction

    def get_all_transactions(self) -> list[Transaction]:
        """Return all transactions."""
        return self._transaction_repository.get_all()

    def get_report_by_category(self) -> dict[str, Decimal]:
        """Sum expenses per category (income is excluded)."""
        report: dict[str, Decimal] = {}
        for tx in self._transaction_repository.get_all():
            if not tx.is_income:
                report[tx.category] = report.get(tx.category, Decimal("0")) + tx.amount
        return report

    def get_transaction_by_id(self, transaction_id: str) -> Transaction | None:
        """Fetch a single transaction by its id."""
        return self._transaction_repository.get_by_id(transaction_id)

    def get_transactions_by_date_range(
        self, from_date: date | None = None, to_date: date | None = None
    ) -> list[Transaction]:
        """Return transactions filtered by date range.

        None means 'no bound' on that side.
        """
        return self._transaction_repository.get_by_date_range(from_date, to_date)

    def delete_transaction(self, transaction_id: str) -> None:
        """Delete a transaction by id."""
        self._transaction_repository.delete(transaction_id)

    def update_transaction(self, transaction: Transaction) -> None:
        """Update an existing transaction.

        The transaction object must have the same id as the one being updated.
        """
        self._transaction_repository.update(transaction)

    def set_budget(self, category: str, month: str, limit: Decimal) -> Budget:
        """Set or update a monthly budget for a category."""
        budget = Budget(category=category, month=month, limit=limit)
        self._budget_repository.add(budget)
        return budget

    def get_budget(self, category: str, month: str) -> Budget | None:
        """Get budget for a specific category and month."""
        return self._budget_repository.get_by_category_and_month(category, month)

    def get_remaining_budget(self, category: str, month: str) -> Decimal | None:
        """Calculate remaining budget for a category in a month.

        Returns None if no budget is set.
        """
        from datetime import timedelta

        budget = self.get_budget(category, month)
        if budget is None:
            return None

        # Get all expenses for this category in the month
        from_date = date.fromisoformat(f"{month}-01")

        # Calculate last day of month (first day of next month minus 1 day)
        if month.endswith("-12"):
            next_month_first = date(int(month[:4]) + 1, 1, 1)
        else:
            next_month = int(month[5:7]) + 1
            next_month_first = date(int(month[:4]), next_month, 1)

        to_date = next_month_first - timedelta(days=1)

        transactions = self._transaction_repository.get_by_date_range(
            from_date, to_date
        )

        total_expenses = Decimal("0")
        for tx in transactions:
            if tx.category == category and not tx.is_income:
                total_expenses += tx.amount

        return budget.limit - total_expenses

    def get_budget_report(self, month: str) -> dict[str, dict[str, Decimal]]:
        """Get budget report for all categories in a month.

        Returns dict with category -> {budget, spent, remaining}.
        """
        budgets = self._budget_repository.get_all_by_month(month)
        report = {}

        for budget in budgets:
            remaining = self.get_remaining_budget(budget.category, month)
            if remaining is not None:
                spent = budget.limit - remaining
                report[budget.category] = {
                    "budget": budget.limit,
                    "spent": spent,
                    "remaining": remaining,
                }

        return report
