"""Regression test for a documented bug fix.

Bug: Previously, when importing a CSV file with an invalid row in the middle,
the valid rows before it were already saved to the database, breaking atomicity.
Fix: We now parse the entire file first (import_csv_safely), and only then
save transactions. If any row is invalid, nothing is saved.
"""

import io

import pytest

from expense_tracker.application.service import ExpenseService
from expense_tracker.domain.exceptions import InvalidRowError
from expense_tracker.utils.csv_importer import import_csv_safely


def test_csv_import_is_atomic(service: ExpenseService) -> None:
    """If CSV has an invalid row, no transactions should be saved.

    This is the regression test for the partial-import bug.
    """
    csv_data = (
        "amount,category,date,is_income\n"
        "100,Food,2024-01-15,false\n"
        "200,Transport,2024-01-16,false\n"
        "INVALID_AMOUNT,Food,2024-01-17,false\n"
        "300,Entertainment,2024-01-18,false\n"
    )
    file = io.StringIO(csv_data)

    with pytest.raises(InvalidRowError):
        transactions = import_csv_safely(file)
        for tx in transactions:
            service.add_transaction(
                amount=tx.amount,
                category=tx.category,
                transaction_date=tx.date,
                is_income=tx.is_income,
            )

    # KEY INVARIANT: database must be empty because import failed
    assert len(service.get_all_transactions()) == 0


def test_csv_import_success(service: ExpenseService) -> None:
    """Valid CSV is imported completely."""
    csv_data = (
        "amount,category,date,is_income\n"
        "100,Food,2024-01-15,false\n"
        "200,Transport,2024-01-16,false\n"
    )
    file = io.StringIO(csv_data)
    transactions = import_csv_safely(file)
    for tx in transactions:
        service.add_transaction(
            amount=tx.amount,
            category=tx.category,
            transaction_date=tx.date,
            is_income=tx.is_income,
        )
    assert len(service.get_all_transactions()) == 2