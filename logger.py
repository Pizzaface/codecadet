"""Centralized logging configuration for the application.

This module provides a consistent logging interface across the application,
replacing bare except blocks with proper error logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """Setup and return a configured logger.

    Args:
        name: Logger name (typically __name__ from the calling module)
        log_level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


def setup_file_logger(
    name: str,
    log_file: Optional[Path] = None,
    log_level: int = logging.INFO
) -> logging.Logger:
    """Setup a logger that writes to both console and file.

    Args:
        name: Logger name
        log_file: Path to log file (default: logs/app.log in app directory)
        log_level: Logging level

    Returns:
        Configured logger instance
    """
    logger = setup_logger(name, log_level)

    # File handler
    if log_file is None:
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "app.log"

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


# Default application logger
app_logger = setup_logger('codecadet')
