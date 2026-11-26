"""SQLite implementation of the TransactionRepository protocol."""

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from expense_tracker.domain.models import Transaction

DEFAULT_DB_PATH = "expenses.db"


def get_db_path() -> str:
    """Database path from the environment, never hard-coded secrets."""
    return os.environ.get("EXPENSE_DB_PATH", DEFAULT_DB_PATH)


class SQLiteTransactionRepository:
    """Stores transactions in a SQLite file (or in-memory for tests)."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # For in-memory DB we must keep one connection alive,
        # otherwise the database disappears when the connection closes.
        self._in_memory = (db_path == ":memory:")
        self._conn: sqlite3.Connection | None = None
        if self._in_memory:
            self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create the table if it does not exist yet."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    amount TEXT NOT NULL,
                    category TEXT NOT NULL,
                    date TEXT NOT NULL,
                    is_income INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a connection and guarantee it is closed (even on error).

        For in-memory databases we reuse the single persistent connection,
        because closing it would destroy the database.
        """
        if self._in_memory and self._conn is not None:
            yield self._conn
            return

        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def add(self, transaction: Transaction) -> None:
        """Insert one transaction."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO transactions VALUES (?, ?, ?, ?, ?)",
                (
                    transaction.id,
                    str(transaction.amount),
                    transaction.category,
                    transaction.date.isoformat(),
                    int(transaction.is_income),
                ),
            )
            conn.commit()

    def get_all(self) -> list[Transaction]:
        """Return every stored transaction."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, amount, category, date, is_income FROM transactions"
            )
            return [self._row_to_transaction(row) for row in cursor.fetchall()]

    def get_by_category(self, category: str) -> list[Transaction]:
        """Return transactions of one category."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, amount, category, date, is_income "
                "FROM transactions WHERE category = ?",
                (category,),
            )
            return [self._row_to_transaction(row) for row in cursor.fetchall()]

    def delete(self, transaction_id: str) -> None:
        """Remove one transaction by id."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()

    @staticmethod
    def _row_to_transaction(row: tuple[str, str, str, str, int]) -> Transaction:
        """Convert a database row back into a Transaction object."""
        return Transaction(
            amount=Decimal(row[1]),
            category=row[2],
            date=date.fromisoformat(row[3]),
            is_income=bool(row[4]),
            id=row[0],
        )

    def close(self) -> None:
        """Explicitly close the persistent connection (useful for tests)."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None