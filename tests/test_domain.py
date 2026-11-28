"""Tests for domain models and invariants."""

from datetime import date
from decimal import Decimal

import pytest

from expense_tracker.domain.exceptions import InvalidAmountError
from expense_tracker.domain.models import Transaction


def test_transaction_creation_valid() -> None:
    """Valid transaction is created successfully."""
    tx = Transaction(
        amount=Decimal("100.50"),
        category="Food",
        date=date(2024, 1, 15),
        is_income=False,
    )
    assert tx.amount == Decimal("100.50")
    assert tx.category == "Food"


def test_transaction_zero_amount_raises() -> None:
    """Zero amount violates invariant — must raise."""
    with pytest.raises(InvalidAmountError):
        Transaction(
            amount=Decimal("0"),
            category="Food",
            date=date.today(),
            is_income=False,
        )


def test_transaction_negative_amount_raises() -> None:
    """Negative amount violates invariant — must raise."""
    with pytest.raises(InvalidAmountError):
        Transaction(
            amount=Decimal("-50"),
            category="Food",
            date=date.today(),
            is_income=False,
        )


def test_transaction_empty_category_raises() -> None:
    """Empty category violates invariant — must raise."""
    with pytest.raises(ValueError):
        Transaction(
            amount=Decimal("100"),
            category="",
            date=date.today(),
            is_income=False,
        )


def test_transaction_equality_by_id() -> None:
    """Two transactions with same id are equal."""
    tx1 = Transaction(
        id="same-id",
        amount=Decimal("100"),
        category="Food",
        date=date.today(),
        is_income=False,
    )
    tx2 = Transaction(
        id="same-id",
        amount=Decimal("200"),
        category="Transport",
        date=date.today(),
        is_income=True,
    )
    assert tx1 == tx2


def test_transaction_immutability() -> None:
    """Frozen dataclass prevents mutation."""
    tx = Transaction(
        amount=Decimal("100"),
        category="Food",
        date=date.today(),
        is_income=False,
    )
    with pytest.raises(AttributeError):
        tx.amount = Decimal("200")  # type: ignore[misc]
