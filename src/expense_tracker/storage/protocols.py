"""Storage protocols: contracts implemented by concrete repositories."""

from datetime import date
from typing import Protocol

from expense_tracker.domain.models import Budget, Transaction


class TransactionRepository(Protocol):
    """Contract for transaction storage.

    The service depends on this Protocol, not on SQLite. This lets us
    swap real storage for a temporary file in tests (dependency inversion).
    """

    def add(self, transaction: Transaction) -> None: ...

    def get_all(self) -> list[Transaction]: ...

    def get_by_category(self, category: str) -> list[Transaction]: ...

    def delete(self, transaction_id: str) -> None: ...

    def update(self, transaction: Transaction) -> None: ...

    def get_by_id(self, transaction_id: str) -> Transaction | None: ...

    def get_by_date_range(
        self, from_date: date | None, to_date: date | None
    ) -> list[Transaction]: ...


class BudgetRepository(Protocol):
    """Contract for budget storage.

    Budgets are stored separately from transactions to allow
    independent management of monthly limits.
    """

    def add(self, budget: Budget) -> None: ...

    def get_by_category_and_month(self, category: str, month: str) -> Budget | None: ...

    def get_all_by_month(self, month: str) -> list[Budget]: ...

    def delete(self, category: str, month: str) -> None: ...
