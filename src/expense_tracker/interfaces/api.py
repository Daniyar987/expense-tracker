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

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Expense Tracker API", version="1.0.0")

# Lazy service: created only when first request arrives, not on import.
_service: ExpenseService | None = None


def get_service() -> ExpenseService:
    """Return the shared service, creating it on first use."""
    global _service
    if _service is None:
        _service = ExpenseService(SQLiteTransactionRepository(get_db_path()))
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
def list_transactions() -> list[TransactionOut]:
    """List all transactions over HTTP."""
    return [_to_out(tx) for tx in get_service().get_all_transactions()]


@app.get("/report", response_model=list[ReportOut])
def get_report() -> list[ReportOut]:
    """Expense report by category."""
    report = get_service().get_report_by_category()
    return [
        ReportOut(category=cat, total=str(total))
        for cat, total in report.items()
    ]


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: str) -> dict[str, str]:
    """Delete a transaction by id."""
    try:
        get_service().delete_transaction(transaction_id)
    except ExpenseTrackerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "id": transaction_id}