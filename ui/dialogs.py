"""Dialog components for Git Worktree Manager."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
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
        add_tooltip(
            self.path_entry,
            "Enter the full path where the new worktree should be created.\nSupports clipboard paste (Ctrl+V).",
        )
        add_tooltip_to_button(browse_btn, "Browse for a directory to create the worktree")

        # Branch section
        branch_label = QLabel("Branch (new or existing):")
        form_layout.addWidget(branch_label, 2, 0, 1, 2)

        self.branch_entry = QLineEdit()
        self.branch_entry.setMaximumWidth(300)
        form_layout.addWidget(self.branch_entry, 3, 0, 1, 1)

        # Setup clipboard functionality and tooltips for branch
        setup_entry_clipboard(self.branch_entry)
        add_tooltip(
            self.branch_entry,
            "Branch name for the worktree.\nCan be an existing branch or a new branch name.\nSupports clipboard paste (Ctrl+V).",
        )

        # Base ref section
        base_label = QLabel("Starting point (optional, e.g. main or origin/main):")
        form_layout.addWidget(base_label, 4, 0, 1, 2)

        self.base_entry = QLineEdit()
        self.base_entry.setMaximumWidth(300)
        form_layout.addWidget(self.base_entry, 5, 0, 1, 1)

        # Setup clipboard functionality and tooltips for base
        setup_entry_clipboard(self.base_entry)
        add_tooltip(
            self.base_entry,
            "Starting point for new branch (optional).\nExamples: 'main', 'origin/main', commit hash.\nLeave empty to use current HEAD.\nSupports clipboard paste (Ctrl+V).",
        )

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
        chosen = QFileDialog.getExistingDirectory(self, "Choose new worktree directory", init_dir)
        if chosen:
            self.path_entry.setText(chosen)

    def _accept(self):
        """Handle dialog acceptance."""
        path = self.path_entry.text().strip()
        if not path:
            QMessageBox.critical(
                self, "Missing path", "Please choose a target directory for the new worktree."
            )
            return

        branch = self.branch_entry.text().strip() or None
        base = self.base_entry.text().strip() or None
        self.result = (Path(path), branch, base)
        self.accept()


class AgentConfigDialog(QDialog):
    """Dialog for configuring coding agents."""

    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.config = config

        # Import agent config functions
        from config import (
            get_coding_agents,
            get_default_agent,
            remove_agent_config,
            set_agent_config,
            set_default_agent,
        )

        self.get_coding_agents = get_coding_agents
        self.get_default_agent = get_default_agent
        self.set_agent_config = set_agent_config
        self.remove_agent_config = remove_agent_config
        self.set_default_agent = set_default_agent

        self._setup_ui()
        self._apply_dark_theme()
        self._load_agents()
        self._load_preferences()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Preferences")
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Main content in horizontal layout
        main_layout = QHBoxLayout()

        # Left side - Agent list
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Agents:"))

        self.agent_list = QListWidget()
        self.agent_list.setMinimumWidth(200)
        self.agent_list.setMaximumHeight(200)
        self.agent_list.currentItemChanged.connect(self._on_agent_selection_changed)
        left_layout.addWidget(self.agent_list)

        # Buttons for agent management
        agent_btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_agent)
        agent_btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_agent)
        self.remove_btn.setEnabled(False)
        agent_btn_layout.addWidget(self.remove_btn)

        left_layout.addLayout(agent_btn_layout)
        main_layout.addLayout(left_layout)

        # Vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Right side - Agent configuration
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Configuration:"))

        # Agent details form
        form_layout = QGridLayout()

        # Agent ID (read-only for existing agents)
        form_layout.addWidget(QLabel("ID:"), 0, 0)
        self.id_entry = QLineEdit()
        form_layout.addWidget(self.id_entry, 0, 1)

        # Agent name
        form_layout.addWidget(QLabel("Name:"), 1, 0)
        self.name_entry = QLineEdit()
        form_layout.addWidget(self.name_entry, 1, 1)

        # Command
        form_layout.addWidget(QLabel("Command:"), 2, 0)
        self.command_entry = QLineEdit()
        form_layout.addWidget(self.command_entry, 2, 1)

        # Enabled checkbox
        self.enabled_checkbox = QCheckBox("Enabled")
        form_layout.addWidget(self.enabled_checkbox, 3, 0, 1, 2)

        # Default agent selector
        form_layout.addWidget(QLabel("Default agent:"), 4, 0)
        self.default_combo = QComboBox()
        self.default_combo.currentIndexChanged.connect(self._on_default_changed)
        form_layout.addWidget(self.default_combo, 4, 1)

        # Embed terminal checkbox (moved from Preferences menu)
        self.embed_checkbox = QCheckBox("Embed terminal when possible (Linux + xterm)")
        form_layout.addWidget(self.embed_checkbox, 5, 0, 1, 2)

        right_layout.addLayout(form_layout)

        # Save button for individual agent
        self.save_agent_btn = QPushButton("Save Agent")
        self.save_agent_btn.clicked.connect(self._save_current_agent)
        self.save_agent_btn.setEnabled(False)
        right_layout.addWidget(self.save_agent_btn)

        right_layout.addStretch()
        main_layout.addLayout(right_layout)
        layout.addLayout(main_layout)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._save_and_accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

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
                padding: 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #7c7fff;
            }
            QListWidget {
                background-color: #151823;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #2a2d3a;
            }
            QListWidget::item:selected {
                background-color: #7c7fff;
                color: #ffffff;
            }
            QComboBox {
                background-color: #151823;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
            }
            QComboBox:focus {
                border: 2px solid #7c7fff;
            }
            QCheckBox {
                color: #e6e7ee;
                font-size: 11px;
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
            QPushButton:disabled {
                background-color: #0a0c10;
                color: #555;
                border: 1px solid #333;
            }
            QFrame[frameShape="5"] {
                color: #404757;
                border: none;
                background-color: #404757;
                max-width: 1px;
            }
        """)

    def _load_agents(self):
        """Load agents into the list."""
        self.agent_list.clear()
        agents = self.get_coding_agents(self.config)
        default_agent = self.get_default_agent(self.config)

        for agent_id, agent_config in agents.items():
            name = agent_config.get("name", agent_id)
            enabled = agent_config.get("enabled", True)
            item_text = name
            if agent_id == default_agent:
                item_text += " (default)"
            if not enabled:
                item_text += " (disabled)"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, agent_id)
            self.agent_list.addItem(item)

        # Update default combo
        self._update_default_combo()

        # Select first item if available
        if self.agent_list.count() > 0:
            self.agent_list.setCurrentRow(0)

    def _update_default_combo(self):
        """Update the default agent combo box."""
        # Temporarily block signals to prevent recursion
        self.default_combo.blockSignals(True)

        self.default_combo.clear()
        agents = self.get_coding_agents(self.config)
        default_agent = self.get_default_agent(self.config)

        for agent_id, agent_config in agents.items():
            if agent_config.get("enabled", True):
                name = agent_config.get("name", agent_id)
                self.default_combo.addItem(name, agent_id)

        # Set current selection
        for i in range(self.default_combo.count()):
            if self.default_combo.itemData(i) == default_agent:
                self.default_combo.setCurrentIndex(i)
                break

        # Re-enable signals
        self.default_combo.blockSignals(False)

    def _on_agent_selection_changed(self, current, previous):
        """Handle agent selection change."""
        if current is None:
            self._clear_form()
            self.save_agent_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            return

        agent_id = current.data(Qt.UserRole)
        agent_config = self.get_coding_agents(self.config).get(agent_id, {})

        # Fill form
        self.id_entry.setText(agent_id)
        self.id_entry.setReadOnly(True)  # Can't change existing agent IDs
        self.name_entry.setText(agent_config.get("name", ""))
        self.command_entry.setText(agent_config.get("command", ""))
        self.enabled_checkbox.setChecked(agent_config.get("enabled", True))

        self.save_agent_btn.setEnabled(True)
        self.remove_btn.setEnabled(agent_id != "claude")  # Can't remove claude

    def _clear_form(self):
        """Clear the agent configuration form."""
        self.id_entry.clear()
        self.id_entry.setReadOnly(False)
        self.name_entry.clear()
        self.command_entry.clear()
        self.enabled_checkbox.setChecked(True)

    def _add_agent(self):
        """Add a new agent."""
        self.agent_list.clearSelection()
        self._clear_form()
        self.id_entry.setPlaceholderText("e.g. cursor, copilot")
        self.name_entry.setPlaceholderText("e.g. Cursor AI")
        self.command_entry.setPlaceholderText("e.g. cursor")
        self.save_agent_btn.setEnabled(True)
        self.remove_btn.setEnabled(False)

    def _remove_agent(self):
        """Remove the selected agent."""
        current = self.agent_list.currentItem()
        if current is None:
            return

        agent_id = current.data(Qt.UserRole)
        if agent_id == "claude":
            QMessageBox.warning(self, "Cannot Remove", "Cannot remove the Claude agent.")
            return

        reply = QMessageBox.question(
            self,
            "Remove Agent",
            f"Are you sure you want to remove the '{agent_id}' agent?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.remove_agent_config(self.config, agent_id)
            self._load_agents()
            self._clear_form()

    def _save_current_agent(self):
        """Save the current agent configuration."""
        agent_id = self.id_entry.text().strip()
        name = self.name_entry.text().strip()
        command = self.command_entry.text().strip()
        enabled = self.enabled_checkbox.isChecked()

        if not agent_id or not name or not command:
            QMessageBox.warning(
                self, "Invalid Configuration", "Please fill in all fields (ID, Name, and Command)."
            )
            return

        self.set_agent_config(self.config, agent_id, name, command, enabled)
        self._load_agents()

        # Select the saved agent
        for i in range(self.agent_list.count()):
            item = self.agent_list.item(i)
            if item.data(Qt.UserRole) == agent_id:
                self.agent_list.setCurrentItem(item)
                break

    def _on_default_changed(self, index):
        """Handle default agent change."""
        if index >= 0:
            agent_id = self.default_combo.itemData(index)
            if agent_id and agent_id != self.get_default_agent(self.config):
                self.set_default_agent(self.config, agent_id)
                # Refresh the agent list to show new default indicator
                current_selection = self.agent_list.currentItem()
                selected_agent_id = None
                if current_selection:
                    try:
                        selected_agent_id = current_selection.data(Qt.UserRole)
                    except RuntimeError:
                        # Item was deleted, ignore
                        selected_agent_id = None

                self._load_agents()

                # Restore selection if it still exists
                if selected_agent_id:
                    for i in range(self.agent_list.count()):
                        item = self.agent_list.item(i)
                        if item and item.data(Qt.UserRole) == selected_agent_id:
                            self.agent_list.setCurrentItem(item)
                            break

    def _load_preferences(self):
        """Load general preferences."""
        self.embed_checkbox.setChecked(bool(self.config.get("embed_terminal", True)))

    def _save_and_accept(self):
        """Save all preferences and accept the dialog."""
        # Save the embed terminal preference
        self.config["embed_terminal"] = self.embed_checkbox.isChecked()
        self.accept()
