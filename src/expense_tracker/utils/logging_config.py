"""Logging configuration: logs go to a file, not into CLI output."""

import logging
import os
import sys
from pathlib import Path


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging.

    Logs are written to a file and to stderr, so CLI stdout stays clean.
    No tokens or sensitive data are logged.
    """
    log_dir = Path(os.environ.get("EXPENSE_LOG_DIR", Path.home()))
    log_file = log_dir / "expense_tracker.log"

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )