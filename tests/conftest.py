"""Pytest fixtures for the expense tracker tests."""

from pathlib import Path

import pytest

from expense_tracker.application.service import ExpenseService
from expense_tracker.storage.sqlite_repo import SQLiteBudgetRepository, SQLiteTransactionRepository


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Temporary database file for tests.

    Both repositories share the same file so they see each other's tables.
    """
    return str(tmp_path / "test.db")


@pytest.fixture
def in_memory_repo(db_path: str) -> SQLiteTransactionRepository:
    """SQLite transaction repository for isolated tests."""
    return SQLiteTransactionRepository(db_path)


@pytest.fixture
def budget_repo(db_path: str) -> SQLiteBudgetRepository:
    """SQLite budget repository for isolated tests."""
    return SQLiteBudgetRepository(db_path)


@pytest.fixture
def service(in_memory_repo: SQLiteTransactionRepository, budget_repo: SQLiteBudgetRepository) -> ExpenseService:
    """Service wired to both repositories."""
    return ExpenseService(in_memory_repo, budget_repo)