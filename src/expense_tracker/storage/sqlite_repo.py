"""SQLite implementation of the TransactionRepository protocol."""

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from expense_tracker.domain.exceptions import ExpenseTrackerError
from expense_tracker.domain.models import Budget, Transaction

DEFAULT_DB_PATH = "expenses.db"


def get_db_path() -> str:
    """Database path from the environment, never hard-coded secrets."""
    return os.environ.get("EXPENSE_DB_PATH", DEFAULT_DB_PATH)


class SQLiteTransactionRepository:
    """Stores transactions in a SQLite file (or in-memory for tests)."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._in_memory = db_path == ":memory:"
        self._conn: sqlite3.Connection | None = None
        if self._in_memory:
            self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create the transactions table if it does not exist yet."""
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
        """Open a connection and guarantee it is closed (even on error)."""
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

    def get_by_id(self, transaction_id: str) -> Transaction | None:
        """Return a single transaction by id or prefix.

        Returns None if not found or ambiguous.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, amount, category, date, is_income "
                "FROM transactions WHERE id LIKE ?",
                (transaction_id + "%",),
            )
            rows = cursor.fetchall()
            if len(rows) == 0:
                return None
            if len(rows) > 1:
                return None
            return self._row_to_transaction(rows[0])

    def get_by_date_range(
        self, from_date: date | None, to_date: date | None
    ) -> list[Transaction]:
        """Return transactions within an inclusive date range."""
        query = "SELECT id, amount, category, date, is_income FROM transactions"
        conditions: list[str] = []
        params: list[str] = []
        if from_date is not None:
            conditions.append("date >= ?")
            params.append(from_date.isoformat())
        if to_date is not None:
            conditions.append("date <= ?")
            params.append(to_date.isoformat())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_transaction(row) for row in cursor.fetchall()]

    def delete(self, transaction_id: str) -> None:
        """Remove one transaction by id."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()

    def update(self, transaction: Transaction) -> None:
        """Update an existing transaction."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE transactions "
                "SET amount = ?, category = ?, date = ?, is_income = ? "
                "WHERE id = ?",
                (
                    str(transaction.amount),
                    transaction.category,
                    transaction.date.isoformat(),
                    int(transaction.is_income),
                    transaction.id,
                ),
            )
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


class SQLiteBudgetRepository:
    """SQLite implementation of BudgetRepository."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_budgets_table()

    def _init_budgets_table(self) -> None:
        """Create the budgets table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    month TEXT NOT NULL,
                    budget_limit TEXT NOT NULL,
                    UNIQUE(category, month)
                )
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection, creating one if needed."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        yield self._conn

    def add(self, budget: Budget) -> None:
        """Add or replace a budget."""
        with self._get_connection() as conn:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO budgets "
                    "(id, category, month, budget_limit) "
                    "VALUES (?, ?, ?, ?)",
                    (budget.id, budget.category, budget.month, str(budget.limit)),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ExpenseTrackerError(f"Failed to save budget: {exc}") from exc

    def get_by_category_and_month(self, category: str, month: str) -> Budget | None:
        """Return a budget for a specific category and month."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, category, month, budget_limit "
                "FROM budgets WHERE category = ? AND month = ?",
                (category, month),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_budget(row)

    def get_all_by_month(self, month: str) -> list[Budget]:
        """Return all budgets for a specific month."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, category, month, budget_limit FROM budgets WHERE month = ?",
                (month,),
            )
            return [self._row_to_budget(row) for row in cursor.fetchall()]

    def delete(self, category: str, month: str) -> None:
        """Delete a budget by category and month."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM budgets WHERE category = ? AND month = ?",
                (category, month),
            )
            conn.commit()

    @staticmethod
    def _row_to_budget(row: sqlite3.Row) -> Budget:
        """Convert a database row to a Budget object."""
        return Budget(
            id=row["id"],
            category=row["category"],
            month=row["month"],
            limit=Decimal(row["budget_limit"]),
        )


    def close(self) -> None:
        """Explicitly close the persistent connection (useful for tests)."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
