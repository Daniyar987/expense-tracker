"""FastAPI web interface (interface #2). Shares the same service."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from expense_tracker.application.service import ExpenseService
from expense_tracker.domain.exceptions import ExpenseTrackerError
from expense_tracker.domain.models import Transaction
from expense_tracker.storage.sqlite_repo import (
    SQLiteTransactionRepository,
    get_db_path,
)
from expense_tracker.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Expense Tracker API", version="1.0.0")

# Lazy service: created only when first request arrives, not on import.
_service: ExpenseService | None = None


def get_service() -> ExpenseService:
    """Return the shared service, creating it on first use."""
    global _service
    if _service is None:
        setup_logging()
        from expense_tracker.storage.sqlite_repo import SQLiteBudgetRepository

        _service = ExpenseService(
            SQLiteTransactionRepository(get_db_path()),
            SQLiteBudgetRepository(get_db_path()),
        )
    return _service


class TransactionCreate(BaseModel):
    """Request body for creating a transaction."""

    amount: str = Field(..., description="Amount as string for precision")
    category: str
    date: str | None = Field(default=None, description="YYYY-MM-DD")
    is_income: bool = False


class TransactionOut(BaseModel):
    """Response model for a transaction."""

    id: str
    amount: str
    category: str
    date: str
    is_income: bool


class ReportOut(BaseModel):
    """Response model for one category line."""

    category: str
    total: str


def _to_out(tx: Transaction) -> TransactionOut:
    """Convert domain model to response model."""
    return TransactionOut(
        id=tx.id,
        amount=str(tx.amount),
        category=tx.category,
        date=tx.date.isoformat(),
        is_income=tx.is_income,
    )


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction. All fields are optional."""

    amount: str | None = Field(
        default=None, description="Amount as string for precision"
    )
    category: str | None = None
    date: str | None = Field(default=None, description="YYYY-MM-DD")
    is_income: bool | None = None


class BudgetCreate(BaseModel):
    """Request body for creating/updating a budget."""

    category: str
    month: str = Field(..., description="Month in YYYY-MM format")
    limit: str = Field(..., description="Budget limit as string for precision")


class BudgetOut(BaseModel):
    """Response model for a budget."""

    category: str
    month: str
    limit: str


class BudgetReportItem(BaseModel):
    """One line in the budget report."""

    category: str
    budget: str
    spent: str
    remaining: str
    status: str  # "OK" or "OVER"


@app.post("/transactions", response_model=TransactionOut)
def create_transaction(data: TransactionCreate) -> TransactionOut:
    """Create a transaction over HTTP."""
    try:
        amount = Decimal(data.amount)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid amount: {data.amount}"
        ) from exc
    tx_date = date.fromisoformat(data.date) if data.date else date.today()
    try:
        tx = get_service().add_transaction(
            amount=amount,
            category=data.category,
            transaction_date=tx_date,
            is_income=data.is_income,
        )
    except ExpenseTrackerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logger.info("Created transaction %s via API", tx.id)
    return _to_out(tx)


@app.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[TransactionOut]:
    """List all transactions, optionally filtered by date range."""
    parsed_from = date.fromisoformat(from_date) if from_date else None
    parsed_to = date.fromisoformat(to_date) if to_date else None
    transactions = get_service().get_transactions_by_date_range(parsed_from, parsed_to)
    return [_to_out(tx) for tx in transactions]


@app.get("/report", response_model=list[ReportOut])
def get_report(
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[ReportOut]:
    """Expense report by category, optionally filtered by date range."""
    parsed_from = date.fromisoformat(from_date) if from_date else None
    parsed_to = date.fromisoformat(to_date) if to_date else None
    transactions = get_service().get_transactions_by_date_range(parsed_from, parsed_to)

    report: dict[str, Decimal] = {}
    for tx in transactions:
        if not tx.is_income:
            report[tx.category] = report.get(tx.category, Decimal("0")) + tx.amount

    return [
        ReportOut(category=cat, total=str(total))
        for cat, total in sorted(report.items())
    ]


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: str) -> dict[str, str]:
    """Delete a transaction by id."""
    try:
        get_service().delete_transaction(transaction_id)
    except ExpenseTrackerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "id": transaction_id}


@app.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: str, update: TransactionUpdate
) -> TransactionOut:
    """Update an existing transaction."""
    existing = get_service().get_transaction_by_id(transaction_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    try:
        amount = Decimal(update.amount) if update.amount else existing.amount
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid amount: {update.amount}"
        ) from exc

    category = update.category if update.category else existing.category
    tx_date = date.fromisoformat(update.date) if update.date else existing.date
    is_income = update.is_income if update.is_income is not None else existing.is_income

    updated = Transaction(
        id=existing.id,
        amount=amount,
        category=category,
        date=tx_date,
        is_income=is_income,
    )
    get_service().update_transaction(updated)
    return _to_out(updated)


@app.post("/budgets", response_model=BudgetOut)
def set_budget(data: BudgetCreate) -> BudgetOut:
    """Set or update a monthly budget for a category."""
    try:
        limit = Decimal(data.limit)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid limit: {data.limit}"
        ) from exc

    try:
        budget = get_service().set_budget(data.category, data.month, limit)
    except ExpenseTrackerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return BudgetOut(
        category=budget.category, month=budget.month, limit=str(budget.limit)
    )


@app.get("/budgets/report/{month}", response_model=list[BudgetReportItem])
def budget_report(month: str) -> list[BudgetReportItem]:
    """Budget report for all categories in a month."""
    report = get_service().get_budget_report(month)
    if not report:
        return []

    result = []
    for category, data in sorted(report.items()):
        remaining = data["remaining"]
        status = "OK" if remaining >= 0 else "OVER"
        result.append(
            BudgetReportItem(
                category=category,
                budget=str(data["budget"]),
                spent=str(data["spent"]),
                remaining=str(remaining),
                status=status,
            )
        )
    return result


@app.get("/budgets/{month}", response_model=list[BudgetOut])
def get_budgets_by_month(month: str) -> list[BudgetOut]:
    """Get all budgets for a specific month."""
    budgets = get_service()._budget_repository.get_all_by_month(month)
    return [
        BudgetOut(category=b.category, month=b.month, limit=str(b.limit))
        for b in budgets
    ]


@app.get("/budgets/{category}/{month}", response_model=BudgetOut)
def get_budget(category: str, month: str) -> BudgetOut:
    """Get budget for a specific category and month."""
    budget = get_service().get_budget(category, month)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    return BudgetOut(
        category=budget.category, month=budget.month, limit=str(budget.limit)
    )


@app.delete("/budgets/{category}/{month}")
def delete_budget(category: str, month: str) -> dict[str, str]:
    """Delete a budget for a specific category and month."""
    budget = get_service().get_budget(category, month)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")

    get_service()._budget_repository.delete(category, month)
    return {"status": "deleted", "category": category, "month": month}
