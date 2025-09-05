"""Sidebar components for worktree management."""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QDialog, QLineEdit, QListWidget, QTextEdit,
    QDialogButtonBox, QMessageBox, QListWidgetItem, QScrollArea
)

from models import WorktreeInfo
from git_utils import checkout_branch
from config import push_recent_branch, get_recent_branches, save_config
from graphite_utils import (is_graphite_repo, get_current_branch_info, GRAPHITE_COMMANDS,
                           run_graphite_command, run_safe_graphite_command,
                           suggest_conflict_resolution)
from .tooltip import add_tooltip_to_button, add_tooltip


class SimpleWorktreePanel(QFrame):
    """Simple worktree panel."""
    
    # Custom signal for selection
    selected = Signal(object)  # WorktreeInfo
    branch_change_requested = Signal(object)  # SimpleWorktreePanel

    def __init__(self, parent, info: WorktreeInfo):
        super().__init__(parent)
        self.info = info
        self.is_selected = False
        self._setup_ui()
        self._apply_dark_theme()

    def _setup_ui(self):
        """Build simple panel UI with dark theme."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        
        # Name row with attention indicator
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)

        name = self.info.path.name or str(self.info.path)
        if self.info.is_main:
            name += " (main)"

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        name_row.addWidget(self.name_label)

        name_row.addStretch()

        # Attention dot (hidden by default)
        self.attn_label = QLabel("●")
        self.attn_label.setStyleSheet("color: #f4be6c; font-size: 14px;")
        self.attn_label.setVisible(False)
        name_row.addWidget(self.attn_label)

        layout.addLayout(name_row)

        # Branch row with button
        branch_layout = QHBoxLayout()
        branch_layout.setContentsMargins(0, 0, 0, 0)
        
        branch_text = "detached" if not self.info.branch else self.info.branch.replace("refs/heads/", "")
        self.branch_label = QLabel(f"Branch: {branch_text}")
        self.branch_label.setFont(QFont("Arial", 10))
        branch_layout.addWidget(self.branch_label)

        if not self.info.locked:
            change_btn = QPushButton("Switch")
            change_btn.setFont(QFont("Arial", 8))
            change_btn.clicked.connect(lambda: self.branch_change_requested.emit(self))
            branch_layout.addWidget(change_btn)
            add_tooltip_to_button(change_btn, "Switch to a different branch in this worktree")

        branch_layout.addStretch()
        layout.addLayout(branch_layout)

        # Path
        path_text = str(self.info.path)
        if len(path_text) > 50:
            path_text = "..." + path_text[-47:]
        path_label = QLabel(path_text)
        path_label.setFont(QFont("Arial", 9))
        layout.addWidget(path_label)
        
        # Make panel clickable
        self.mousePressEvent = self._on_click

    def _apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QFrame {
                background-color: #151823;
                border: none;
                border-radius: 4px;
                margin: 2px;
                padding: 5px;
            }
            QLabel {
                color: #e6e7ee;
                background-color: transparent;
                border: none;
            }
            QPushButton {
                background-color: #1a1f2e;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #7c7fff;
                color: #ffffff;
            }
        """)

    def _on_click(self, event):
        """Handle click events."""
        self.selected.emit(self.info)

    def set_selected(self, selected: bool):
        """Update selection state with dark theme."""
        self.is_selected = selected
        if selected:
            self.setStyleSheet(self.styleSheet() + """
                QFrame {
                    background-color: #26304a !important;
                    border: none !important;
                }
            """)
            # Clear attention indicator when switching to this worktree
            self.set_attention(False)
        else:
            self._apply_dark_theme()

    def update_branch_display(self, new_branch: str):
        """Update the branch display after a branch switch."""
        branch_text = "detached" if not new_branch else new_branch.replace("refs/heads/", "")
        self.branch_label.setText(f"Branch: {branch_text}")

    def set_attention(self, on: bool):
        """Show or hide the attention dot."""
        if hasattr(self, 'attn_label'):
            self.attn_label.setVisible(bool(on))


class SimpleWorktreeSidebar(QWidget):
    """Simple sidebar for worktree management."""

    def __init__(self, parent, on_worktree_select, get_repo_root, get_branches):
        super().__init__(parent)
        self.on_worktree_select = on_worktree_select
        self.get_repo_root = get_repo_root
        self.get_branches = get_branches
        self.panels: list[SimpleWorktreePanel] = []
        self.selected_panel: SimpleWorktreePanel | None = None
        self.is_graphite_repo = False
        self.config = {}  # Will be set by main window

        self._setup_ui()
        self._apply_dark_theme()
    
    def set_config(self, config):
        """Set the configuration object for recent branches tracking."""
        self.config = config

    def _setup_ui(self):
        """Build simple sidebar UI with dark theme."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("Worktrees")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Graphite commands section (will be populated when repo is loaded)
        self.graphite_frame = QWidget()
        self.graphite_layout = QVBoxLayout(self.graphite_frame)
        self.graphite_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.graphite_frame)
        
        # Content area with scroll support
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(2)
        self.content_layout.addStretch()
        
        scroll_area.setWidget(self.content_widget)
        layout.addWidget(scroll_area, 1)  # stretch factor 1

    def _apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            SimpleWorktreeSidebar {
                background-color: #0f1115;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
            }
            QWidget {
                background-color: #0f1115;
                color: #e6e7ee;
            }
            QLabel {
                color: #e6e7ee;
            }
            QScrollArea {
                border: none;
                background-color: #0f1115;
            }
            QScrollBar:vertical {
                background-color: #151823;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #404757;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7c7fff;
            }
        """)

    def update_worktrees(self, infos: list[WorktreeInfo]):
        """Update worktree list and Graphite integration."""
        # Clear existing panels
        for panel in self.panels:
            panel.setParent(None)
            panel.deleteLater()
        self.panels.clear()
        self.selected_panel = None

        # Check if this is a Graphite repo
        repo_root = self.get_repo_root()
        if repo_root:
            self.is_graphite_repo = is_graphite_repo(repo_root)
            self._update_graphite_ui()

        # Create new panels
        for info in infos:
            panel = SimpleWorktreePanel(self.content_widget, info)
            panel.selected.connect(self._on_panel_selected)
            panel.branch_change_requested.connect(self._on_branch_change)
            
            # Insert before the stretch
            self.content_layout.insertWidget(self.content_layout.count() - 1, panel)
            self.panels.append(panel)

    def set_attention_for_path(self, path: Path, on: bool):
        """Set or clear the attention indicator for a given worktree path."""
        for panel in self.panels:
            if panel.info.path == path:
                panel.set_attention(on)
                break
    
    def _update_graphite_ui(self):
        """Update the Graphite commands UI section."""
        # Clear existing graphite widgets
        while self.graphite_layout.count():
            child = self.graphite_layout.takeAt(0)
            widget = child.widget() if child else None
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif child:
                # Handle layout items that aren't widgets
                child_layout = child.layout()
                if child_layout:
                    self._clear_layout(child_layout)
    
    def _clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget() if child else None
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif child:
                child_layout = child.layout()
                if child_layout:
                    self._clear_layout(child_layout)
            
        if not self.is_graphite_repo:
            return
        
        # Graphite header
        graphite_label = QLabel("📊 Graphite")
        graphite_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        graphite_label.setStyleSheet("color: #7c7fff;")
        self.graphite_layout.addWidget(graphite_label)
        
        # Create buttons for common Graphite commands
        
        # Row 1: Navigation with clearer labels
        nav_layout = QHBoxLayout()
        nav_commands = [
            ("up", "Up", "Move up one branch in the current stack"),
            ("down", "Down", "Move down one branch in the current stack"),
            ("top", "Top", "Go to the top branch of the current stack"),
            ("bottom", "Base", "Go to the bottom/base branch of the current stack")
        ]
        
        for cmd_key, label, tooltip in nav_commands:
            if cmd_key in GRAPHITE_COMMANDS:
                cmd_info = GRAPHITE_COMMANDS[cmd_key]
                btn = QPushButton(f"{cmd_info['icon']}\n{label}")
                btn.setFont(QFont("Arial", 8))
                btn.setFixedSize(60, 50)
                btn.clicked.connect(lambda checked, k=cmd_key: self._run_graphite_command(k))
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1a1f2e;
                        color: #e6e7ee;
                        border: 1px solid #404757;
                        border-radius: 4px;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background-color: #7c7fff;
                        color: #ffffff;
                    }
                """)
                nav_layout.addWidget(btn)
                add_tooltip_to_button(btn, tooltip)
        
        self.graphite_layout.addLayout(nav_layout)
        
        # Row 2: Stack management with clearer labels
        stack_layout = QHBoxLayout()
        stack_commands = [
            ("log", "Log", "Show visual stack representation with branch relationships"),
            ("sync", "Sync", "Synchronize the stack with remote repository (may cause conflicts)"),
            ("restack", "Rebase", "Rebase the entire stack to resolve conflicts (may cause conflicts)"),
            ("submit", "Submit", "Create/update pull requests for the current stack")
        ]
        
        for cmd_key, label, tooltip in stack_commands:
            if cmd_key in GRAPHITE_COMMANDS:
                cmd_info = GRAPHITE_COMMANDS[cmd_key]
                btn = QPushButton(f"{cmd_info['icon']}\n{label}")
                btn.setFont(QFont("Arial", 8))
                btn.setFixedSize(60, 50)
                btn.clicked.connect(lambda checked, k=cmd_key: self._run_graphite_command(k))
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1a1f2e;
                        color: #e6e7ee;
                        border: 1px solid #404757;
                        border-radius: 4px;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background-color: #7c7fff;
                        color: #ffffff;
                    }
                """)
                stack_layout.addWidget(btn)
                add_tooltip_to_button(btn, tooltip)
        
        self.graphite_layout.addLayout(stack_layout)
    
    def _run_graphite_command(self, command_key: str):
        """Run a Graphite command with conflict checking."""
        repo_root = self.get_repo_root()
        if not repo_root:
            QMessageBox.critical(self, "No Repository", "No repository selected.")
            return
            
        if command_key not in GRAPHITE_COMMANDS:
            return
            
        cmd_info = GRAPHITE_COMMANDS[command_key]
        
        # For potentially unsafe commands, use conflict checking
        if not cmd_info.get("safe", True):
            self._run_safe_graphite_command(command_key, cmd_info)
        else:
            # For safe commands, run directly
            self._run_basic_graphite_command(command_key, cmd_info)
    
    def _run_basic_graphite_command(self, command_key: str, cmd_info: dict):
        """Run a basic Graphite command without conflict checking."""
        repo_root = self.get_repo_root()
        
        # Check if this command allows interactive mode
        allow_interactive = cmd_info.get("allow_interactive", False)
        success, output = run_graphite_command(repo_root, cmd_info["cmd"], allow_interactive)
        
        if success:
            if command_key == "log":
                self._show_stack_visualization(output)
            else:
                QMessageBox.information(self, "Graphite", f"{cmd_info['desc']} completed successfully!\n\n{output}")
            
            # Auto-refresh after commands that might change branches
            if command_key in ["up", "down", "top", "bottom", "checkout", "sync"]:
                self._auto_refresh_after_branch_switch()
        else:
            # Special handling for multiple branches scenario
            if "Multiple top branches found" in output:
                QMessageBox.warning(self, "Multiple Top Branches", output)
            else:
                QMessageBox.critical(self, "Graphite Error", f"Failed to {cmd_info['desc']}:\n\n{output}")
    
    def _run_safe_graphite_command(self, command_key: str, cmd_info: dict):
        """Run a potentially unsafe Graphite command with conflict checking."""
        repo_root = self.get_repo_root()
        
        # Get main app to access worktree info
        main_app = self._get_main_app()
        if not main_app or not hasattr(main_app, 'infos'):
            # Fallback to basic command if we can't get worktree info
            self._run_basic_graphite_command(command_key, cmd_info)
            return
            
        # Show loading message for longer operations
        if command_key in ["sync", "restack", "submit"]:
            QMessageBox.information(self, "Graphite", f"Checking for conflicts before {cmd_info['desc'].lower()}...")
        
        # Run with conflict checking
        success, output, conflicts = run_safe_graphite_command(repo_root, cmd_info["cmd"], main_app.infos)
        
        if conflicts:
            # Show conflict resolution dialog
            self._show_conflict_resolution_dialog(command_key, cmd_info, conflicts, repo_root)
        elif success:
            QMessageBox.information(self, "Graphite", f"{cmd_info['desc']} completed successfully!\n\n{output}")
            # Auto-refresh after successful operations
            if command_key in ["restack", "sync", "modify"]:
                self._auto_refresh_after_branch_switch()
        else:
            QMessageBox.critical(self, "Graphite Error", f"Failed to {cmd_info['desc']}:\n\n{output}")
    
    def _show_conflict_resolution_dialog(self, command_key: str, cmd_info: dict, conflicts: dict, repo_root):
        """Show a dialog to help resolve worktree conflicts."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Worktree Conflict Resolution")
        dialog.setModal(True)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header_label = QLabel("⚠️ Worktree Conflict Detected")
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #ff9500;")
        layout.addWidget(header_label)
        
        desc_label = QLabel(f"Cannot {cmd_info['desc'].lower()} due to branch conflicts")
        desc_label.setFont(QFont("Arial", 10))
        layout.addWidget(desc_label)
        
        # Conflicts list
        conflicts_label = QLabel("Conflicting branches:")
        conflicts_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(conflicts_label)
        
        conflicts_text = QTextEdit()
        conflicts_text.setMaximumHeight(200)
        conflicts_text.setFont(QFont("Consolas", 9))
        
        # Show conflicts
        conflict_info = []
        for branch, conflict_data in conflicts.items():
            worktree_name = conflict_data['worktree_name']
            conflict_info.append(f"• {branch} → checked out in '{worktree_name}' worktree")
        
        conflicts_text.setPlainText("\n".join(conflict_info))
        conflicts_text.setReadOnly(True)
        layout.addWidget(conflicts_text)
        
        # Suggestions
        suggestions = suggest_conflict_resolution(conflicts, repo_root)
        if suggestions:
            suggestions_label = QLabel("Suggested resolution:")
            suggestions_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            layout.addWidget(suggestions_label)
            
            suggestions_text = QTextEdit()
            suggestions_text.setMaximumHeight(100)
            suggestions_text.setFont(QFont("Arial", 9))
            suggestions_text.setPlainText("\n".join(suggestions))
            suggestions_text.setReadOnly(True)
            layout.addWidget(suggestions_text)
        
        # Buttons
        button_box = QDialogButtonBox()
        
        cancel_btn = button_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        force_btn = button_box.addButton("Force Run Anyway", QDialogButtonBox.ButtonRole.AcceptRole)
        worktrees_btn = button_box.addButton("Open Worktrees", QDialogButtonBox.ButtonRole.ActionRole)
        
        def force_run():
            dialog.accept()
            success, output = run_graphite_command(repo_root, cmd_info["cmd"])
            if success:
                QMessageBox.information(self, "Graphite", f"{cmd_info['desc']} completed!\n\n{output}")
                if command_key in ["restack", "sync", "modify"]:
                    self._auto_refresh_after_branch_switch()
            else:
                QMessageBox.critical(self, "Graphite Error", f"Failed to {cmd_info['desc']}:\n\n{output}")
        
        def highlight_conflicts():
            dialog.accept()
            self._highlight_conflicts(conflicts)
        
        cancel_btn.clicked.connect(dialog.reject)
        force_btn.clicked.connect(force_run)
        worktrees_btn.clicked.connect(highlight_conflicts)
        
        layout.addWidget(button_box)
        
        # Apply dark theme
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #e6e7ee;
            }
            QLabel {
                color: #e6e7ee;
            }
            QTextEdit {
                background-color: #151823;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #1a1f2e;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #20273a;
            }
        """)
        
        dialog.exec()
    
    def _highlight_conflicts(self, conflicts: dict):
        """Highlight conflicting worktrees in the main UI."""
        main_app = self._get_main_app()
        if main_app:
            conflict_names = [data['worktree_name'] for data in conflicts.values()]
            main_app._set_status(f"Conflicting worktrees: {', '.join(conflict_names)}")
    
    def _show_stack_visualization(self, output: str):
        """Show stack visualization in a dedicated dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Graphite Stack Visualization")
        dialog.setModal(False)
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header = QLabel("📊 Current Stack")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #7c7fff;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Stack visualization
        text_widget = QTextEdit()
        text_widget.setFont(QFont("Consolas", 10))
        text_widget.setPlainText(output)
        text_widget.setReadOnly(True)
        layout.addWidget(text_widget)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c7fff;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #6b6bff;
            }
        """)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Apply dark theme
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #e6e7ee;
            }
            QLabel {
                color: #e6e7ee;
            }
            QTextEdit {
                background-color: #151823;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
            }
        """)
        
        dialog.show()

    def _on_panel_selected(self, info: WorktreeInfo):
        """Handle panel selection."""
        # Deselect previous
        if self.selected_panel:
            self.selected_panel.set_selected(False)

        # Find and select new panel
        for panel in self.panels:
            if panel.info == info:
                self.selected_panel = panel
                panel.set_selected(True)
                break

        # Notify main window
        self.on_worktree_select(info)

    def _on_branch_change(self, panel: SimpleWorktreePanel):
        """Handle branch change with enhanced UI and recent branches."""
        repo_root = self.get_repo_root()
        if not repo_root:
            QMessageBox.critical(self, "No Repository", "No repository selected.")
            return

        try:
            all_branches = self.get_branches()
            if not all_branches:
                QMessageBox.information(self, "No Branches", "No branches found.")
                return

            # Get current branch
            current_branch = panel.info.branch
            if current_branch and current_branch.startswith("refs/heads/"):
                current_branch = current_branch[11:]

            # Get recent branches for this repo
            recent_branches = get_recent_branches(self.config, repo_root) if self.config else []

            # Create branch selection dialog
            dialog = BranchSelectionDialog(self, panel, all_branches, current_branch, recent_branches, repo_root, self.config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._auto_refresh_after_branch_switch()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get branches: {e}")

    def _auto_refresh_after_branch_switch(self):
        """Auto-refresh the main application after switching branches with enhanced reliability."""
        # Get the main app instance and refresh
        main_app = self._get_main_app()
        if main_app and hasattr(main_app, 'refresh'):
            # Use QTimer to delay refresh slightly to ensure git operation is complete
            QTimer.singleShot(100, main_app.refresh)
            # Also update status to show the refresh happened
            QTimer.singleShot(200, lambda: main_app._set_status("Auto-refreshed after branch switch"))

    def _get_main_app(self):
        """Get the main App instance by traversing the widget hierarchy."""
        widget = self
        while widget:
            if hasattr(widget, 'refresh') and hasattr(widget, 'repo_root'):
                return widget  # Found the main App instance
            widget = widget.parent()
        return None

    def get_selected_worktree(self) -> Path | None:
        """Get selected worktree."""
        return self.selected_panel.info.path if self.selected_panel else None


class BranchSelectionDialog(QDialog):
    """Dialog for selecting branches with search functionality."""
    
    def __init__(self, parent, panel, all_branches, current_branch, recent_branches, repo_root, config):
        super().__init__(parent)
        self.panel = panel
        self.all_branches = all_branches
        self.current_branch = current_branch
        self.recent_branches = recent_branches
        self.repo_root = repo_root
        self.config = config
        
        self._setup_ui()
        self._apply_dark_theme()
        
    def _setup_ui(self):
        """Setup the branch selection dialog UI."""
        self.setWindowTitle("Switch Branch")
        self.setModal(True)
        self.resize(450, 600)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Switch branch for:")
        header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header_label)
        
        path_label = QLabel(self.panel.info.path.name)
        path_label.setStyleSheet("color: #7c7fff;")
        layout.addWidget(path_label)
        
        # Search
        search_label = QLabel("Search branches:")
        search_label.setFont(QFont("Arial", 9))
        layout.addWidget(search_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self._update_listbox)
        layout.addWidget(self.search_entry)
        
        # Branch list
        self.listbox = QListWidget()
        self.listbox.itemDoubleClicked.connect(self._do_switch)
        layout.addWidget(self.listbox)
        
        # Buttons
        button_box = QDialogButtonBox()
        cancel_btn = button_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        switch_btn = button_box.addButton("Switch", QDialogButtonBox.ButtonRole.AcceptRole)
        switch_btn.setDefault(True)
        
        cancel_btn.clicked.connect(self.reject)
        switch_btn.clicked.connect(self._do_switch)
        
        layout.addWidget(button_box)
        
        # Populate branches
        self._organize_branches()
        self._update_listbox()
        self.search_entry.setFocus()
    
    def _apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #e6e7ee;
            }
            QLabel {
                color: #e6e7ee;
            }
            QLineEdit {
                background-color: #151823;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 2px solid #7c7fff;
            }
            QListWidget {
                background-color: #151823;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                selection-background-color: #7c7fff;
                selection-color: #ffffff;
            }
            QListWidget::item {
                padding: 4px;
                border: none;
            }
            QListWidget::item:hover {
                background-color: #20273a;
            }
            QPushButton {
                background-color: #1a1f2e;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #20273a;
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
    
    def _organize_branches(self):
        """Organize branches: current first, then recent, then all others."""
        self.organized_branches = []
        
        # Current branch first (with indicator)
        if self.current_branch and self.current_branch in self.all_branches:
            self.organized_branches.append(f"★ {self.current_branch} (current)")
            
        # Recent branches next (excluding current)
        for branch in self.recent_branches:
            if branch != self.current_branch and branch in self.all_branches:
                self.organized_branches.append(f"🕒 {branch}")
        
        # Add separator if we have recent branches
        if len(self.organized_branches) > 1:
            self.organized_branches.append("─" * 30)
        
        # All other branches
        for branch in sorted(self.all_branches):
            if branch != self.current_branch and branch not in self.recent_branches:
                self.organized_branches.append(branch)
    
    def _update_listbox(self):
        """Update the listbox with filtered branches."""
        self.listbox.clear()
        search_text = self.search_entry.text().lower()
        
        current_selection = None
        for i, branch_display in enumerate(self.organized_branches):
            if search_text in branch_display.lower():
                item = QListWidgetItem(branch_display)
                if branch_display.startswith("─"):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    item.setData(Qt.ItemDataRole.UserRole, "separator")
                self.listbox.addItem(item)
                
                if branch_display.startswith("★"):
                    current_selection = self.listbox.count() - 1
        
        # Select current branch if it's in the filtered results
        if current_selection is not None:
            self.listbox.setCurrentRow(current_selection)
        elif self.listbox.count() > 0:
            # Select first non-separator item
            for i in range(self.listbox.count()):
                item = self.listbox.item(i)
                if not item.data(Qt.ItemDataRole.UserRole) == "separator":
                    self.listbox.setCurrentRow(i)
                    break
    
    def _do_switch(self):
        """Switch to the selected branch."""
        current_item = self.listbox.currentItem()
        if not current_item or current_item.data(Qt.ItemDataRole.UserRole) == "separator":
            return
            
        branch_display = current_item.text()
        
        # Extract actual branch name
        branch = branch_display
        if branch.startswith("★ "):
            branch = branch[2:].split(" (current)")[0]
        elif branch.startswith("🕒 "):
            branch = branch[2:]
        
        try:
            checkout_branch(self.panel.info.path, branch)
            
            # Track this branch switch in recent branches
            if self.config:
                push_recent_branch(self.config, self.repo_root, branch)
                save_config(self.config)
            
            QMessageBox.information(self, "Success", f"Switched to: {branch}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
