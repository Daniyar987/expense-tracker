"""CSV export functionality for transactions."""

import csv
import io

from expense_tracker.domain.models import Transaction


def export_transactions_to_csv(transactions: list[Transaction]) -> str:
    """Export transactions to CSV format.

    Returns a CSV string with columns: id, amount, category, date, is_income.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["id", "amount", "category", "date", "is_income"])

    # Data rows
    for tx in transactions:
        writer.writerow(
            [
                tx.id,
                str(tx.amount),
                tx.category,
                tx.date.isoformat(),
                tx.is_income,
            ]
        )

    return output.getvalue()
