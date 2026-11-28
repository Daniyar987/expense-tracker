"""Domain models for the expense tracker."""

from __future__ import annotations

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


@dataclass(frozen=True)
class Budget:
    """Monthly budget for a category.

    Invariant: limit must be strictly positive.
    """

    category: str
    month: str  # Format: "YYYY-MM"
    limit: Decimal
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Validate invariants right after the object is created."""
        if not self.category or not self.category.strip():
            raise ValueError("Category cannot be empty")
        if self.limit <= Decimal("0"):
            raise InvalidAmountError(
                f"Budget limit must be strictly positive, got {self.limit}"
            )
        if not self.month or len(self.month) != 7 or self.month[4] != "-":
            raise ValueError("Month must be in YYYY-MM format")