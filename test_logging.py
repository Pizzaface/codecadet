#!/usr/bin/env python3
"""Test script to verify logging system functionality."""

from logging_config import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO", log_to_file=True, log_to_console=True)
logger = get_logger(__name__)

# Test different log levels
logger.debug("Debug message - should appear in file only")
logger.info("Info message - logging system working correctly")
logger.warning("Warning message - test warning")
logger.error("Error message - test error")

# Test exception logging
try:
    raise ValueError("Test exception for logging")
except Exception as e:
    logger.error(f"Caught test exception: {e}", exc_info=True)

print("✅ Logging system test completed successfully")
