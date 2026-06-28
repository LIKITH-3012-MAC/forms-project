"""
Structured Logging Configuration
=================================
Provides centralized logging setup for the Sakra Forms application.

Features:
- JSON formatted logs if `python-json-logger` is installed, otherwise
  falls back to a standard text format.
- Console handler (stdout) for development and container environments.
- RotatingFileHandler writing to `logs/app.log` (10 MB, 5 backups).
- Named loggers for each application subsystem:
  sakra.api, sakra.db, sakra.email, sakra.ai, sakra.security
- Utility function `mask_sensitive()` to redact sensitive fields from dicts.
- Utility function `get_logger(name)` for convenient logger retrieval.

Usage:
    from logging_config import setup_logging, get_logger

    setup_logging()
    logger = get_logger("sakra.api")
    logger.info("Application started")
"""

import logging
import logging.handlers
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Standard log format (fallback when python-json-logger is unavailable)
STANDARD_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Named loggers for application subsystems
LOGGER_NAMES = [
    "sakra.api",
    "sakra.db",
    "sakra.email",
    "sakra.ai",
    "sakra.security",
]

# Fields to mask in log data
SENSITIVE_FIELDS = {"password", "token", "api_key", "secret", "secret_key"}


# ---------------------------------------------------------------------------
# Formatter helpers
# ---------------------------------------------------------------------------

def _create_json_formatter() -> logging.Formatter | None:
    """
    Attempt to create a JSON formatter using python-json-logger.
    Returns None if the package is not installed.
    """
    try:
        from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

        return jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt=DATE_FORMAT,
        )
    except ImportError:
        return None


def _create_standard_formatter() -> logging.Formatter:
    """Create the standard text formatter."""
    return logging.Formatter(fmt=STANDARD_FORMAT, datefmt=DATE_FORMAT)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the application logging system.

    Args:
        level: The root logging level (default: INFO).
    """
    # Ensure the log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Determine formatter
    formatter = _create_json_formatter() or _create_standard_formatter()

    # --- Console handler (stdout) ---
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # --- Rotating file handler ---
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # --- Configure root logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates on re-init
    root_logger.handlers.clear()

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # --- Initialise named loggers ---
    for name in LOGGER_NAMES:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        # Propagate to root so handlers are shared
        logger.propagate = True

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root_logger.info("Logging initialised (level=%s)", logging.getLevelName(level))


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a named logger.

    Args:
        name: Logger name, e.g. ``"sakra.api"``.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


def mask_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a deep copy of *data* with sensitive field values replaced
    by ``***MASKED***``.

    Sensitive fields (case-insensitive): password, token, api_key,
    secret, secret_key.

    Args:
        data: A dictionary potentially containing sensitive values.

    Returns:
        A new dictionary with sensitive values masked.
    """
    masked = deepcopy(data)
    for key in masked:
        if key.lower() in SENSITIVE_FIELDS:
            masked[key] = "***MASKED***"
        elif isinstance(masked[key], dict):
            masked[key] = mask_sensitive(masked[key])
    return masked
