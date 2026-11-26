"""Pytest fixtures for the expense tracker tests."""

import pytest

from expense_tracker.application.service import ExpenseService
from expense_tracker.storage.sqlite_repo import SQLiteTransactionRepository


@pytest.fixture
def in_memory_repo():
    """In-memory SQLite repository for isolated tests.

    This is a substitute for the real storage, allowing tests
    to run without touching the filesystem.
    """
    return SQLiteTransactionRepository(":memory:")


@pytest.fixture
def service(in_memory_repo):
    """Service wired to in-memory repository."""
    return ExpenseService(in_memory_repo)