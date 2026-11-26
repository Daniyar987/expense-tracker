"""Logging configuration: logs go to a file, not into CLI output."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging.

    Logs are written to a file and to stderr, so CLI stdout stays clean.
    No tokens or sensitive data are logged.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("expense_tracker.log", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )