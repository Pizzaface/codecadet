"""Centralized error handling and user feedback system."""

import sys
import traceback
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from logging_config import get_logger
from metrics import record_error

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for user feedback."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better organization."""
    GIT_OPERATION = "git_operation"
    FILE_SYSTEM = "file_system"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    UI_OPERATION = "ui_operation"
    SESSION_MANAGEMENT = "session_management"
    STARTUP = "startup"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    technical_details: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    exception: Optional[Exception] = None
    traceback_str: Optional[str] = None


class ErrorHandler:
    """Centralized error handling and user notification system."""
    
    def __init__(self):
        self.notification_callback: Optional[Callable[[ErrorInfo], None]] = None
        self.crash_reporting_enabled = False
        
    def set_notification_callback(self, callback: Callable[[ErrorInfo], None]):
        """Set callback function for user notifications."""
        self.notification_callback = callback
        logger.debug("Error notification callback registered")
    
    def enable_crash_reporting(self, enabled: bool = True):
        """Enable or disable crash reporting."""
        self.crash_reporting_enabled = enabled
        logger.info(f"Crash reporting {'enabled' if enabled else 'disabled'}")
    
    def handle_error(
        self,
        exception: Exception,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """Handle an error with comprehensive logging and user feedback."""
        
        # Generate traceback
        traceback_str = traceback.format_exc() if exception else None
        
        # Create error info
        error_info = ErrorInfo(
            category=category,
            severity=severity,
            message=str(exception),
            user_message=user_message or self._generate_user_message(exception, category),
            technical_details=traceback_str,
            context=context or {},
            exception=exception,
            traceback_str=traceback_str
        )
        
        # Log the error
        self._log_error(error_info)
        
        # Record metrics
        self._record_error_metrics(error_info)
        
        # Notify user if callback is set
        if self.notification_callback:
            try:
                self.notification_callback(error_info)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")
        
        # Handle crash reporting for critical errors
        if severity == ErrorSeverity.CRITICAL and self.crash_reporting_enabled:
            self._handle_crash_report(error_info)
        
        return error_info
    
    def handle_git_error(
        self,
        exception: Exception,
        operation: str,
        repo_path: Optional[Path] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> ErrorInfo:
        """Handle Git-specific errors with contextual information."""
        context = {
            "operation": operation,
            "repo_path": str(repo_path) if repo_path else None
        }
        
        user_message = self._generate_git_user_message(exception, operation)
        
        return self.handle_error(
            exception=exception,
            category=ErrorCategory.GIT_OPERATION,
            severity=severity,
            user_message=user_message,
            context=context
        )
    
    def handle_file_system_error(
        self,
        exception: Exception,
        operation: str,
        file_path: Optional[Path] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> ErrorInfo:
        """Handle file system errors with contextual information."""
        context = {
            "operation": operation,
            "file_path": str(file_path) if file_path else None
        }
        
        user_message = self._generate_file_system_user_message(exception, operation, file_path)
        
        return self.handle_error(
            exception=exception,
            category=ErrorCategory.FILE_SYSTEM,
            severity=severity,
            user_message=user_message,
            context=context
        )
    
    def handle_configuration_error(
        self,
        exception: Exception,
        config_key: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.WARNING
    ) -> ErrorInfo:
        """Handle configuration-related errors."""
        context = {
            "config_key": config_key
        }
        
        user_message = self._generate_config_user_message(exception, config_key)
        
        return self.handle_error(
            exception=exception,
            category=ErrorCategory.CONFIGURATION,
            severity=severity,
            user_message=user_message,
            context=context
        )
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error information appropriately based on severity."""
        log_message = f"[{error_info.category.value}] {error_info.message}"
        
        if error_info.context:
            log_message += f" | Context: {error_info.context}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=error_info.exception)
        elif error_info.severity == ErrorSeverity.ERROR:
            logger.error(log_message, exc_info=error_info.exception)
        elif error_info.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _record_error_metrics(self, error_info: ErrorInfo):
        """Record error metrics for analysis."""
        try:
            record_error(
                error_type=f"{error_info.category.value}_{type(error_info.exception).__name__}",
                error_message=error_info.message,
                context={
                    "severity": error_info.severity.value,
                    "category": error_info.category.value,
                    **error_info.context
                }
            )
        except Exception as e:
            logger.debug(f"Failed to record error metrics: {e}")
    
    def _handle_crash_report(self, error_info: ErrorInfo):
        """Handle crash reporting for critical errors."""
        try:
            # Create crash report (could be extended to send to external service)
            crash_report = {
                "category": error_info.category.value,
                "severity": error_info.severity.value,
                "message": error_info.message,
                "traceback": error_info.traceback_str,
                "context": error_info.context,
                "python_version": sys.version,
                "platform": sys.platform
            }
            
            logger.critical(f"Crash report generated: {crash_report}")
            
            # Could extend this to write to file or send to crash reporting service
            
        except Exception as e:
            logger.error(f"Failed to generate crash report: {e}")
    
    def _generate_user_message(self, exception: Exception, category: ErrorCategory) -> str:
        """Generate user-friendly error message."""
        exception_type = type(exception).__name__
        
        if category == ErrorCategory.GIT_OPERATION:
            return f"Git operation failed: {str(exception)}"
        elif category == ErrorCategory.FILE_SYSTEM:
            return f"File system error: {str(exception)}"
        elif category == ErrorCategory.CONFIGURATION:
            return f"Configuration error: {str(exception)}"
        elif category == ErrorCategory.NETWORK:
            return f"Network error: {str(exception)}"
        elif category == ErrorCategory.UI_OPERATION:
            return f"Interface error: {str(exception)}"
        elif category == ErrorCategory.SESSION_MANAGEMENT:
            return f"Session management error: {str(exception)}"
        elif category == ErrorCategory.STARTUP:
            return f"Application startup error: {str(exception)}"
        else:
            return f"An unexpected error occurred: {str(exception)}"
    
    def _generate_git_user_message(self, exception: Exception, operation: str) -> str:
        """Generate user-friendly Git error message."""
        error_msg = str(exception).lower()
        
        if "not a git repository" in error_msg:
            return f"The selected directory is not a Git repository. Please choose a valid Git repository."
        elif "permission denied" in error_msg:
            return f"Permission denied while performing Git operation '{operation}'. Check file permissions."
        elif "branch already exists" in error_msg:
            return f"A branch with that name already exists. Please choose a different name."
        elif "worktree already exists" in error_msg:
            return f"A worktree already exists at that location. Please choose a different path."
        elif "network" in error_msg or "connection" in error_msg:
            return f"Network error during Git operation '{operation}'. Check your internet connection."
        else:
            return f"Git operation '{operation}' failed: {str(exception)}"
    
    def _generate_file_system_user_message(
        self, 
        exception: Exception, 
        operation: str, 
        file_path: Optional[Path]
    ) -> str:
        """Generate user-friendly file system error message."""
        error_msg = str(exception).lower()
        path_str = str(file_path) if file_path else "the specified location"
        
        if "permission denied" in error_msg:
            return f"Permission denied accessing {path_str}. Check file permissions."
        elif "no such file or directory" in error_msg:
            return f"File or directory not found: {path_str}"
        elif "disk full" in error_msg or "no space left" in error_msg:
            return f"Not enough disk space to complete operation '{operation}'."
        elif "file exists" in error_msg:
            return f"File already exists at {path_str}. Choose a different location."
        else:
            return f"File system operation '{operation}' failed: {str(exception)}"
    
    def _generate_config_user_message(
        self, 
        exception: Exception, 
        config_key: Optional[str]
    ) -> str:
        """Generate user-friendly configuration error message."""
        key_info = f" for setting '{config_key}'" if config_key else ""
        
        if "json" in str(exception).lower():
            return f"Configuration file contains invalid JSON{key_info}. Please check the syntax."
        elif "validation" in str(exception).lower():
            return f"Invalid configuration value{key_info}. Please check your settings."
        else:
            return f"Configuration error{key_info}: {str(exception)}"


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


def handle_error(
    exception: Exception,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> ErrorInfo:
    """Convenience function to handle errors using the global handler."""
    return _error_handler.handle_error(exception, category, severity, user_message, context)


def handle_git_error(
    exception: Exception,
    operation: str,
    repo_path: Optional[Path] = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR
) -> ErrorInfo:
    """Convenience function to handle Git errors."""
    return _error_handler.handle_git_error(exception, operation, repo_path, severity)


def handle_file_system_error(
    exception: Exception,
    operation: str,
    file_path: Optional[Path] = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR
) -> ErrorInfo:
    """Convenience function to handle file system errors."""
    return _error_handler.handle_file_system_error(exception, operation, file_path, severity)


def handle_configuration_error(
    exception: Exception,
    config_key: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.WARNING
) -> ErrorInfo:
    """Convenience function to handle configuration errors."""
    return _error_handler.handle_configuration_error(exception, config_key, severity)
