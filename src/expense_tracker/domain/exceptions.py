"""Custom exceptions for the expense tracker domain."""


class ExpenseTrackerError(Exception):
    """Base exception for all expense tracker errors."""


class InvalidAmountError(ExpenseTrackerError):
    """Raised when amount is zero or negative."""


class InvalidRowError(ExpenseTrackerError):
    """Raised when a CSV row cannot be parsed."""
