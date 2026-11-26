"""End-to-end tests for the FastAPI interface."""

import os

# Use a separate database for API tests to avoid polluting the real one
os.environ["EXPENSE_DB_PATH"] = "test_api.db"

from fastapi.testclient import TestClient

from expense_tracker.interfaces.api import app

client = TestClient(app)


def test_api_create_and_list() -> None:
    """API can create and list transactions."""
    # 1. Create a transaction via HTTP POST
    response = client.post(
        "/transactions",
        json={
            "amount": "500.00",
            "category": "Food",
            "date": "2024-01-15",
            "is_income": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Food"
    tx_id = data["id"]

    # 2. List all transactions via HTTP GET
    response = client.get("/transactions")
    assert response.status_code == 200
    transactions = response.json()
    assert any(tx["id"] == tx_id for tx in transactions)

    # 3. Cleanup: delete the created transaction
    client.delete(f"/transactions/{tx_id}")


def test_api_invalid_amount_returns_400() -> None:
    """API returns 400 Bad Request for invalid amount."""
    response = client.post(
        "/transactions",
        json={
            "amount": "not-a-number",
            "category": "Food",
            "is_income": False,
        },
    )
    assert response.status_code == 400
    assert "Invalid amount" in response.json()["detail"]