"""Storage protocols: contracts implemented by concrete repositories."""

from typing import Protocol

from expense_tracker.domain.models import Transaction


class TransactionRepository(Protocol):
    """Contract for transaction storage.

    The service depends on this Protocol, not on SQLite. This lets us
    swap real storage for a temporary file in tests (dependency inversion).
    """

    def add(self, transaction: Transaction) -> None: ...

    def get_all(self) -> list[Transaction]: ...

    def get_by_category(self, category: str) -> list[Transaction]: ...

    def delete(self, transaction_id: str) -> None: ...