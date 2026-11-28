"""Extended tests for CSV import with various invalid inputs."""

import io

from expense_tracker.utils.csv_importer import import_csv_safely


def test_csv_import_valid() -> None:
    """Import valid CSV returns transactions."""
    csv_data = "id,amount,category,date,is_income\n,500,Food,2024-01-15,False\n"
    transactions = import_csv_safely(io.StringIO(csv_data))
    assert len(transactions) == 1
    assert transactions[0].amount == 500
    assert transactions[0].category == "Food"


def test_csv_import_negative_amount_skipped() -> None:
    """Rows with negative amount are skipped."""
    csv_data = "id,amount,category,date,is_income\n,-100,Food,2024-01-15,False\n"
    transactions = import_csv_safely(io.StringIO(csv_data))
    assert len(transactions) == 0


def test_csv_import_zero_amount_skipped() -> None:
    """Rows with zero amount are skipped."""
    csv_data = "id,amount,category,date,is_income\n,0,Food,2024-01-15,False\n"
    transactions = import_csv_safely(io.StringIO(csv_data))
    assert len(transactions) == 0


def test_csv_import_empty_category_skipped() -> None:
    """Rows with empty category are skipped."""
    csv_data = "id,amount,category,date,is_income\n,500,,2024-01-15,False\n"
    transactions = import_csv_safely(io.StringIO(csv_data))
    assert len(transactions) == 0


def test_csv_import_invalid_date_skipped() -> None:
    """Rows with invalid date format are skipped."""
    csv_data = "id,amount,category,date,is_income\n,500,Food,not-a-date,False\n"
    transactions = import_csv_safely(io.StringIO(csv_data))
    assert len(transactions) == 0


def test_csv_import_invalid_amount_skipped() -> None:
    """Rows with non-numeric amount are skipped."""
    csv_data = "id,amount,category,date,is_income\n,abc,Food,2024-01-15,False\n"
    transactions = import_csv_safely(io.StringIO(csv_data))
    assert len(transactions) == 0


def test_csv_import_mixed_valid_and_invalid() -> None:
    """Only valid rows are imported, invalid ones are skipped."""
    csv_data = (
        "id,amount,category,date,is_income\n"
        ",500,Food,2024-01-15,False\n"
        ",-100,Food,2024-01-16,False\n"
        ",300,Transport,2024-01-17,False\n"
        ",abc,Food,2024-01-18,False\n"
    )
    transactions = import_csv_safely(io.StringIO(csv_data))
    assert len(transactions) == 2
    categories: list[str] = [tx.category for tx in transactions]
    assert "Food" in categories
    assert "Transport" in categories


def test_csv_import_same_file_twice() -> None:
    """Importing the same file twice creates separate transactions."""
    csv_data = "id,amount,category,date,is_income\n,500,Food,2024-01-15,False\n"

    transactions1 = import_csv_safely(io.StringIO(csv_data))
    transactions2 = import_csv_safely(io.StringIO(csv_data))

    # Both imports succeed, but create separate transactions
    assert len(transactions1) == 1
    assert len(transactions2) == 1
    # IDs are different (new UUID generated each time)
    assert transactions1[0].id != transactions2[0].id
