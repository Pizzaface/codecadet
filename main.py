#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Worktree Manager for Claude Code — v2 (Refactored)
Entry point for the modular application.
"""

import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import App

if __name__ == "__main__":
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Git Worktree Manager for Claude Code")
    app.setApplicationDisplayName("Worktree Manager")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Claude Code Tools")
    
    # Create and show main window
    window = App()
    window.show()
    
    # Run the event loop
    sys.exit(app.exec())
