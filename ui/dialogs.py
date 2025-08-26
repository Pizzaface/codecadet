"""Dialog components for Git Worktree Manager."""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
)

from clipboard import setup_entry_clipboard
from .tooltip import add_tooltip, add_tooltip_to_button


class CreateDialog(QDialog):
    """Dialog for creating a new worktree."""
    
    def __init__(self, parent, repo_root: Path):
        super().__init__(parent)
        self.setWindowTitle("Create worktree")
        self.setModal(True)
        self.repo_root = repo_root
        self.result = None  # (path, branch, base_ref)
        
        self._setup_ui()
        self._apply_dark_theme()
        
        # Set initial focus
        self.path_entry.setFocus()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Create grid layout for form
        form_layout = QGridLayout()
        form_layout.setSpacing(8)
        
        # Path section
        path_label = QLabel("New worktree path:")
        form_layout.addWidget(path_label, 0, 0, 1, 2)
        
        path_row_layout = QHBoxLayout()
        self.path_entry = QLineEdit()
        self.path_entry.setMinimumWidth(400)
        path_row_layout.addWidget(self.path_entry)
        
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_row_layout.addWidget(browse_btn)
        
        form_layout.addLayout(path_row_layout, 1, 0, 1, 2)
        
        # Setup clipboard functionality and tooltips for path
        setup_entry_clipboard(self.path_entry)
        add_tooltip(self.path_entry, "Enter the full path where the new worktree should be created.\nSupports clipboard paste (Ctrl+V).")
        add_tooltip_to_button(browse_btn, "Browse for a directory to create the worktree")
        
        # Branch section
        branch_label = QLabel("Branch (new or existing):")
        form_layout.addWidget(branch_label, 2, 0, 1, 2)
        
        self.branch_entry = QLineEdit()
        self.branch_entry.setMaximumWidth(300)
        form_layout.addWidget(self.branch_entry, 3, 0, 1, 1)
        
        # Setup clipboard functionality and tooltips for branch
        setup_entry_clipboard(self.branch_entry)
        add_tooltip(self.branch_entry, "Branch name for the worktree.\nCan be an existing branch or a new branch name.\nSupports clipboard paste (Ctrl+V).")
        
        # Base ref section
        base_label = QLabel("Starting point (optional, e.g. main or origin/main):")
        form_layout.addWidget(base_label, 4, 0, 1, 2)
        
        self.base_entry = QLineEdit()
        self.base_entry.setMaximumWidth(300)
        form_layout.addWidget(self.base_entry, 5, 0, 1, 1)
        
        # Setup clipboard functionality and tooltips for base
        setup_entry_clipboard(self.base_entry)
        add_tooltip(self.base_entry, "Starting point for new branch (optional).\nExamples: 'main', 'origin/main', commit hash.\nLeave empty to use current HEAD.\nSupports clipboard paste (Ctrl+V).")
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        add_tooltip_to_button(cancel_btn, "Cancel worktree creation")
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self._accept)
        create_btn.setDefault(True)
        button_layout.addWidget(create_btn)
        add_tooltip_to_button(create_btn, "Create the new worktree with the specified settings")
        
        layout.addLayout(button_layout)
        
        # Connect Enter key to accept
        self.path_entry.returnPressed.connect(self._accept)
        self.branch_entry.returnPressed.connect(self._accept)
        self.base_entry.returnPressed.connect(self._accept)
    
    def _apply_dark_theme(self):
        """Apply dark theme styling to the dialog."""
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #e6e7ee;
            }
            QLabel {
                color: #e6e7ee;
                font-size: 11px;
            }
            QLineEdit {
                background-color: #151823;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #7c7fff;
            }
            QPushButton {
                background-color: #1a1f2e;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #20273a;
            }
            QPushButton:pressed {
                background-color: #26304a;
            }
            QPushButton:default {
                background-color: #7c7fff;
                color: #ffffff;
                border: 1px solid #7c7fff;
            }
            QPushButton:default:hover {
                background-color: #6b6bff;
            }
        """)
    
    def _browse(self):
        """Open file dialog to browse for worktree directory."""
        init_dir = str(self.repo_root.parent)
        chosen = QFileDialog.getExistingDirectory(
            self, 
            "Choose new worktree directory", 
            init_dir
        )
        if chosen:
            self.path_entry.setText(chosen)
    
    def _accept(self):
        """Handle dialog acceptance."""
        path = self.path_entry.text().strip()
        if not path:
            QMessageBox.critical(
                self, 
                "Missing path", 
                "Please choose a target directory for the new worktree."
            )
            return
        
        branch = self.branch_entry.text().strip() or None
        base = self.base_entry.text().strip() or None
        self.result = (Path(path), branch, base)
        self.accept()
