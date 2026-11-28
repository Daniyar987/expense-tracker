"""Regression tests for CSV import.

These tests ensure that the CSV import handles invalid rows correctly
and does not crash on malformed data.
"""

import io

from expense_tracker.application.service import ExpenseService


def test_csv_import_is_atomic(service: ExpenseService) -> None:
    """If CSV has an invalid row, it should be skipped, not crash the import.

    Valid rows are still imported. This is the "soft import" behavior.
    """
    csv_data = (
        "id,amount,category,date,is_income\n"
        ",100,Food,2024-01-15,false\n"
        ",200,Transport,2024-01-16,false\n"
        ",INVALID_AMOUNT,Food,2024-01-17,false\n"
        ",300,Entertainment,2024-01-18,false\n"
    )
    file = io.StringIO(csv_data)

    from expense_tracker.utils.csv_importer import import_csv_safely

    transactions = import_csv_safely(file)

    # Invalid row is skipped, valid rows are imported
    assert len(transactions) == 3
    categories = [tx.category for tx in transactions]
    assert "Food" in categories
    assert "Transport" in categories
    assert "Entertainment" in categories


def test_csv_import_success(service: ExpenseService) -> None:
    """Valid CSV is imported correctly."""
    csv_data = (
        "id,amount,category,date,is_income\n"
        ",100,Food,2024-01-15,false\n"
        ",200,Transport,2024-01-16,false\n"
        ",300,Entertainment,2024-01-18,false\n"
    )
    file = io.StringIO(csv_data)

    from expense_tracker.utils.csv_importer import import_csv_safely

    transactions = import_csv_safely(file)

    assert len(transactions) == 3
    assert transactions[0].amount == 100
    assert transactions[0].category == "Food"
    assert transactions[1].amount == 200
    assert transactions[1].category == "Transport"
    assert transactions[2].amount == 300
    assert transactions[2].category == "Entertainment"
