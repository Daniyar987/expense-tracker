"""Tests for application service."""

from datetime import date
from decimal import Decimal

from expense_tracker.application.service import ExpenseService


def test_add_transaction(service: ExpenseService) -> None:
    """Adding a transaction persists it."""
    tx = service.add_transaction(
        amount=Decimal("500"),
        category="Food",
        transaction_date=date(2024, 1, 15),
        is_income=False,
    )
    all_txs = service.get_all_transactions()
    assert len(all_txs) == 1
    assert all_txs[0].id == tx.id


def test_report_aggregates_by_category(service: ExpenseService) -> None:
    """Report sums expenses per category."""
    service.add_transaction(Decimal("100"), "Food", date.today(), False)
    service.add_transaction(Decimal("200"), "Food", date.today(), False)
    service.add_transaction(Decimal("50"), "Transport", date.today(), False)
    service.add_transaction(Decimal("1000"), "Salary", date.today(), True)

    report = service.get_report_by_category()
    assert report["Food"] == Decimal("300")
    assert report["Transport"] == Decimal("50")
    assert "Salary" not in report  # income is not in expense report


def test_delete_transaction(service: ExpenseService) -> None:
    """Deleted transaction is removed from storage."""
    tx = service.add_transaction(Decimal("100"), "Food", date.today(), False)
    service.delete_transaction(tx.id)
    assert len(service.get_all_transactions()) == 0