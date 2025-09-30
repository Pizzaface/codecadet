#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Worktree Manager for Claude Code — v2 (Refactored)
Entry point for the modular application.
"""

import sys
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import App
from logging_config import setup_logging, get_logger, configure_qt_logging
from config import _config_dir
from metrics import initialize_metrics, finalize_metrics, record_startup_time

# Setup logging
setup_logging(level="INFO", log_to_file=True, log_to_console=True)
logger = get_logger(__name__)

if __name__ == "__main__":
    startup_start_time = time.time()
    
    try:
        logger.info("Starting Git Worktree Manager application")
        
        # Initialize metrics system
        metrics_collector = initialize_metrics(_config_dir(), enable_telemetry=False)
        logger.info("Metrics system initialized")
        
        # Create QApplication instance
        app = QApplication(sys.argv)
        
        # Configure Qt logging
        configure_qt_logging()
        
        # Set application properties
        app.setApplicationName("Git Worktree Manager for Claude Code")
        app.setApplicationDisplayName("Worktree Manager")
        app.setApplicationVersion("2.0")
        app.setOrganizationName("Claude Code Tools")
        
        # Set application icon
        icon_path = Path(__file__).parent / "assets" / "icon.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            logger.debug(f"Application icon loaded from {icon_path}")
        else:
            logger.warning(f"Application icon not found at {icon_path}")
        
        # Record startup time
        startup_time_ms = (time.time() - startup_start_time) * 1000
        record_startup_time(startup_time_ms)
        logger.info(f"Application startup completed in {startup_time_ms:.1f}ms")
        
        # Create and show main window
        logger.info("Creating main application window")
        window = App()
        window.show()
        
        # Run the event loop
        logger.info("Starting application event loop")
        exit_code = app.exec()
        
        # Finalize metrics before exit
        finalize_metrics()
        logger.info(f"Application exiting with code {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Fatal error during application startup: {e}", exc_info=True)
        # Record startup error if metrics are available
        try:
            from metrics import record_error
            record_error("startup_error", str(e), {"startup_time_ms": (time.time() - startup_start_time) * 1000})
            finalize_metrics()
        except:
            pass
        sys.exit(1)




