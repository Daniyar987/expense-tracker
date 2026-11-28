"""CSV import functionality for transactions.

Uses a generator to parse rows one at a time, giving O(1) memory
complexity regardless of file size. Invalid rows are skipped and logged.
"""

import csv
import logging
from collections.abc import Generator
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TextIO

from expense_tracker.domain.exceptions import InvalidAmountError
from expense_tracker.domain.models import Transaction

logger = logging.getLogger(__name__)


def parse_csv_transactions(file: TextIO) -> Generator[Transaction, None, None]:
    """Yield transactions one row at a time.

    A generator gives O(1) memory complexity: we never load the whole
    file into RAM. CSV columns: id,amount,category,date,is_income

    Invalid rows are skipped and logged.
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
        except (InvalidOperation, ValueError, KeyError, InvalidAmountError) as exc:
            logger.warning("Skipping invalid row %d: %s. Reason: %s", row_num, row, exc)
            continue


def import_csv_safely(file: TextIO) -> list[Transaction]:
    """Import transactions from a CSV file, skipping invalid rows."""
    return list(parse_csv_transactions(file))
