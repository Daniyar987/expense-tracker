"""Tests for budget domain model and service logic."""

from decimal import Decimal

import pytest

from expense_tracker.application.service import ExpenseService
from expense_tracker.domain.exceptions import InvalidAmountError
from expense_tracker.domain.models import Budget, Transaction
from expense_tracker.storage.sqlite_repo import SQLiteBudgetRepository, SQLiteTransactionRepository


# ============================================================================
# Budget model tests
# ============================================================================


def test_budget_creation_valid() -> None:
    """Budget can be created with valid data."""
    budget = Budget(category="Food", month="2024-01", limit=Decimal("1000"))
    assert budget.category == "Food"
    assert budget.month == "2024-01"
    assert budget.limit == Decimal("1000")
    assert budget.id  # Auto-generated UUID


def test_budget_zero_limit_raises() -> None:
    """Budget limit must be strictly positive."""
    with pytest.raises(InvalidAmountError):
        Budget(category="Food", month="2024-01", limit=Decimal("0"))


def test_budget_negative_limit_raises() -> None:
    """Budget limit cannot be negative."""
    with pytest.raises(InvalidAmountError):
        Budget(category="Food", month="2024-01", limit=Decimal("-100"))


def test_budget_empty_category_raises() -> None:
    """Budget category cannot be empty."""
    with pytest.raises(ValueError):
        Budget(category="", month="2024-01", limit=Decimal("1000"))


def test_budget_invalid_month_format_raises() -> None:
    """Budget month must be in YYYY-MM format."""
    with pytest.raises(ValueError):
        Budget(category="Food", month="2024", limit=Decimal("1000"))


def test_budget_immutability() -> None:
    """Budget is frozen and cannot be modified after creation."""
    budget = Budget(category="Food", month="2024-01", limit=Decimal("1000"))
    with pytest.raises(AttributeError):
        budget.limit = Decimal("2000")  # type: ignore[misc]


# ============================================================================
# Budget service tests
# ============================================================================


def test_set_and_get_budget(
    service: ExpenseService,
) -> None:
    """Service can set and retrieve a budget."""
    budget = service.set_budget("Food", "2024-01", Decimal("1000"))
    assert budget.category == "Food"
    assert budget.month == "2024-01"
    assert budget.limit == Decimal("1000")

    retrieved = service.get_budget("Food", "2024-01")
    assert retrieved is not None
    assert retrieved.limit == Decimal("1000")


def test_get_nonexistent_budget_returns_none(
    service: ExpenseService,
) -> None:
    """Service returns None when budget is not set."""
    result = service.get_budget("Food", "2024-01")
    assert result is None


def test_update_existing_budget(
    service: ExpenseService,
) -> None:
    """Setting a budget for the same category and month replaces the old one."""
    service.set_budget("Food", "2024-01", Decimal("1000"))
    service.set_budget("Food", "2024-01", Decimal("2000"))

    budget = service.get_budget("Food", "2024-01")
    assert budget is not None
    assert budget.limit == Decimal("2000")


def test_remaining_budget_positive(
    service: ExpenseService,
) -> None:
    """Remaining budget is positive when spending is under the limit."""
    service.set_budget("Food", "2024-01", Decimal("1000"))
    service.add_transaction(
        amount=Decimal("300"),
        category="Food",
        transaction_date=__import__("datetime").date(2024, 1, 15),
        is_income=False,
    )

    remaining = service.get_remaining_budget("Food", "2024-01")
    assert remaining == Decimal("700")


def test_remaining_budget_exceeded(
    service: ExpenseService,
) -> None:
    """Remaining budget is negative when spending exceeds the limit."""
    service.set_budget("Food", "2024-01", Decimal("1000"))
    service.add_transaction(
        amount=Decimal("1500"),
        category="Food",
        transaction_date=__import__("datetime").date(2024, 1, 15),
        is_income=False,
    )

    remaining = service.get_remaining_budget("Food", "2024-01")
    assert remaining == Decimal("-500")


def test_remaining_budget_no_budget_set(
    service: ExpenseService,
) -> None:
    """Remaining budget returns None when no budget is set."""
    service.add_transaction(
        amount=Decimal("500"),
        category="Food",
        transaction_date=__import__("datetime").date(2024, 1, 15),
        is_income=False,
    )

    remaining = service.get_remaining_budget("Food", "2024-01")
    assert remaining is None


def test_budget_report_multiple_categories(
    service: ExpenseService,
) -> None:
    """Budget report includes all categories with budgets."""
    service.set_budget("Food", "2024-01", Decimal("1000"))
    service.set_budget("Transport", "2024-01", Decimal("500"))

    service.add_transaction(
        amount=Decimal("800"),
        category="Food",
        transaction_date=__import__("datetime").date(2024, 1, 10),
        is_income=False,
    )
    service.add_transaction(
        amount=Decimal("600"),
        category="Transport",
        transaction_date=__import__("datetime").date(2024, 1, 15),
        is_income=False,
    )

    report = service.get_budget_report("2024-01")
    assert "Food" in report
    assert "Transport" in report
    assert report["Food"]["remaining"] == Decimal("200")
    assert report["Transport"]["remaining"] == Decimal("-100")
    assert report["Food"]["spent"] == Decimal("800")
    assert report["Transport"]["spent"] == Decimal("600")


def test_budget_report_excludes_income(
    service: ExpenseService,
) -> None:
    """Budget report only counts expenses, not income."""
    service.set_budget("Salary", "2024-01", Decimal("5000"))
    service.add_transaction(
        amount=Decimal("50000"),
        category="Salary",
        transaction_date=__import__("datetime").date(2024, 1, 1),
        is_income=True,
    )

    report = service.get_budget_report("2024-01")
    assert report["Salary"]["spent"] == Decimal("0")
    assert report["Salary"]["remaining"] == Decimal("5000")