"""CSV import using a generator for lazy, memory-safe parsing."""

import csv
from collections.abc import Generator
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TextIO

from expense_tracker.domain.exceptions import InvalidRowError
from expense_tracker.domain.models import Transaction


def parse_csv_transactions(file: TextIO) -> Generator[Transaction, None, None]:
    """Yield transactions one row at a time.

    A generator gives O(1) memory complexity: we never load the whole
    file into RAM. CSV columns: amount,category,date,is_income
    """
    reader = csv.DictReader(file)
    for row_num, row in enumerate(reader, start=2):
        try:
            amount = Decimal(row["amount"])
            tx_date = date.fromisoformat(row["date"])
            is_income = row["is_income"].strip().lower() in ("true", "1", "yes")
            category = row["category"].strip()
            yield Transaction(
                amount=amount,
                category=category,
                date=tx_date,
                is_income=is_income,
            )
        except (InvalidOperation, ValueError, KeyError) as exc:
            raise InvalidRowError(
                f"Error in row {row_num}: {row}. Reason: {exc}"
            ) from exc


def import_csv_safely(file: TextIO) -> list[Transaction]:
    """Parse the whole file first, then return the list.

    This guarantees atomicity: if any row is invalid, nothing is saved.
    """
    return list(parse_csv_transactions(file))