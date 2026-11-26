"""Domain models for the expense tracker."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from expense_tracker.domain.exceptions import InvalidAmountError


@dataclass(frozen=True)
class Transaction:
    """A single financial transaction.

    frozen=True makes the object immutable after creation, which
    prevents accidentally shared state (no in-place mutation).
    """

    amount: Decimal
    category: str
    date: date = field(default_factory=date.today)
    is_income: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Validate invariants right after the object is created."""
        if self.amount <= Decimal("0"):
            raise InvalidAmountError(
                f"Amount must be strictly positive, got {self.amount}"
            )
        if not self.category or not self.category.strip():
            raise ValueError("Category cannot be empty")

    def __eq__(self, other: object) -> bool:
        """Two transactions are equal when they share the same id."""
        if not isinstance(other, Transaction):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by id so Transaction can be used in sets/dicts."""
        return hash(self.id)