"""Comprehensive logging configuration for Git Worktree Manager."""

import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from config import _config_dir


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
            
        return json.dumps(log_entry, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """Add contextual information to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        # Add process info
        record.pid = sys.platform
        return True


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    json_format: bool = False,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup comprehensive logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        json_format: Whether to use JSON formatting
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
        
    Returns:
        Configured root logger
    """
    # Create logs directory
    log_dir = _config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Setup formatters
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(ContextFilter())
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        log_file = log_dir / "worktree_manager.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ContextFilter())
        root_logger.addHandler(file_handler)
        
        # Separate error log file
        error_log_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(ContextFilter())
        root_logger.addHandler(error_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, message: str, exc_info: bool = True, **kwargs):
    """Log an exception with additional context."""
    extra_data = kwargs
    logger.error(message, exc_info=exc_info, extra={'extra_data': extra_data})


def log_performance(logger: logging.Logger, operation: str, duration: float, **kwargs):
    """Log performance metrics."""
    extra_data = {
        'operation': operation,
        'duration_ms': round(duration * 1000, 2),
        **kwargs
    }
    logger.info(f"Performance: {operation} took {duration:.3f}s", extra={'extra_data': extra_data})


def configure_qt_logging():
    """Configure Qt logging to use our logging system."""
    try:
        from PySide6.QtCore import qInstallMessageHandler, QtMsgType
        
        def qt_message_handler(msg_type: QtMsgType, context, message: str):
            """Handle Qt log messages."""
            qt_logger = get_logger('qt')
            
            if msg_type == QtMsgType.QtDebugMsg:
                qt_logger.debug(f"Qt: {message}")
            elif msg_type == QtMsgType.QtInfoMsg:
                qt_logger.info(f"Qt: {message}")
            elif msg_type == QtMsgType.QtWarningMsg:
                qt_logger.warning(f"Qt: {message}")
            elif msg_type == QtMsgType.QtCriticalMsg:
                qt_logger.error(f"Qt: {message}")
            elif msg_type == QtMsgType.QtFatalMsg:
                qt_logger.critical(f"Qt: {message}")
        
        qInstallMessageHandler(qt_message_handler)
    except ImportError:
        # PySide6 not available, skip Qt logging setup
        pass


# Module-level logger instances for common use
logger = get_logger(__name__)
