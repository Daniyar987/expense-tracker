"""End-to-end tests for the CLI interface.

Runs expense-cli as a subprocess to verify the full workflow
(add → list → report → delete) works end-to-end.
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_cli(args: list[str], db_path: str) -> subprocess.CompletedProcess[str]:
    """Run expense-cli as a subprocess with a temporary database."""
    env = {**os.environ, "EXPENSE_DB_PATH": db_path}
    return subprocess.run(
        [sys.executable, "-m", "expense_tracker.interfaces.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )


def test_cli_e2e_add_list_report(tmp_path: Path) -> None:
    """End-to-end: add transactions, list them, generate report."""
    db = str(tmp_path / "e2e.db")

    # Add two expenses in the same category
    r1 = run_cli(["add", "--amount", "500", "--category", "Food"], db)
    assert r1.returncode == 0, r1.stderr
    assert "Added:" in r1.stdout

    r2 = run_cli(["add", "--amount", "300", "--category", "Food"], db)
    assert r2.returncode == 0, r2.stderr

    # Add one expense in a different category
    r3 = run_cli(["add", "--amount", "200", "--category", "Transport"], db)
    assert r3.returncode == 0, r3.stderr

    # List should show 3 transactions
    r4 = run_cli(["list"], db)
    assert r4.returncode == 0, r4.stderr
    lines = [l for l in r4.stdout.strip().splitlines() if l.strip()]
    assert len(lines) == 3

    # Report should aggregate by category
    r5 = run_cli(["report"], db)
    assert r5.returncode == 0, r5.stderr
    assert "Food: 800" in r5.stdout
    assert "Transport: 200" in r5.stdout


def test_cli_e2e_budget_workflow(tmp_path: Path) -> None:
    """End-to-end: set budget, add expenses, check remaining."""
    db = str(tmp_path / "budget_e2e.db")

    # Set budget
    r1 = run_cli(
        ["budget", "set", "--category", "Food", "--month", "2024-01", "--limit", "1000"],
        db,
    )
    assert r1.returncode == 0, r1.stderr
    assert "Budget set" in r1.stdout

    # Add expense
    r2 = run_cli(
        ["add", "--amount", "700", "--category", "Food", "--date", "2024-01-15"],
        db,
    )
    assert r2.returncode == 0, r2.stderr

    # Check remaining budget
    r3 = run_cli(
        ["budget", "get", "--category", "Food", "--month", "2024-01"],
        db,
    )
    assert r3.returncode == 0, r3.stderr
    assert "Remaining: 300" in r3.stdout


def test_cli_e2e_delete_transaction(tmp_path: Path) -> None:
    """End-to-end: add then delete a transaction."""
    db = str(tmp_path / "delete_e2e.db")

    # Add a transaction
    r1 = run_cli(["add", "--amount", "500", "--category", "Food"], db)
    assert r1.returncode == 0, r1.stderr

    # Get the id from stdout
    tx_id = r1.stdout.strip().split()[1]  # "Added: <id> | ..."

    # Delete it
    r2 = run_cli(["delete", tx_id], db)
    assert r2.returncode == 0, r2.stderr
    assert "Deleted" in r2.stdout

    # List should be empty
    r3 = run_cli(["list"], db)
    assert r3.returncode == 0, r3.stderr
    assert "No transactions" in r3.stdout