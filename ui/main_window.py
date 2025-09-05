"""Main window and application logic."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QUrl
from PySide6.QtGui import QFont, QAction, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QCheckBox, QSplitter,
    QStatusBar, QMenuBar, QMenu, QMessageBox, QFileDialog,
    QInputDialog, QApplication, QDialog
)
from PySide6.QtMultimedia import QSoundEffect

from config import load_config, save_config, push_recent_repo, get_agent_command, get_default_agent, get_coding_agents
from git_utils import git_version_ok, ensure_repo_root, list_worktrees, list_branches
from git_utils import add_worktree, remove_worktree, prune_worktrees
from session import SessionManager
from terminal import open_in_editor, launch_claude_in_terminal
from models import WorktreeInfo
from clipboard import setup_entry_clipboard
from .tooltip import add_tooltip, add_tooltip_to_button, StatusTooltip

from .dialogs import CreateDialog
from .sidebar import SimpleWorktreeSidebar
from .terminal_pane import TerminalPane


class App(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Git Worktree Manager for Claude Code")
        self.resize(1000, 600)
        self.setMinimumSize(880, 520)
        
        # Set window icon
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Config
        self.cfg = load_config()

        # State
        self.repo_root: Path | None = None
        self.infos: list[WorktreeInfo] = []

        # Session manager (must be created before TerminalPane)
        self.session_manager = SessionManager()

        # Setup UI
        self._setup_ui()
        self._apply_theme(self.cfg.get("theme", "dark"))
        self._setup_menus()
        self._setup_shortcuts()
        self._populate_agent_combo()
        
        # Notification sound (shared across app)
        self._notif_sound = QSoundEffect()
        self._last_sound_time = 0.0
        sound_path = Path(__file__).parent.parent / "assets" / "done.wav"
        if sound_path.exists():
            self._notif_sound.setSource(QUrl.fromLocalFile(str(sound_path)))
            self._notif_sound.setVolume(0.5)
        
        # Initial Git check
        if not git_version_ok():
            QMessageBox.warning(
                self,
                "Git version",
                "Git 2.5+ is recommended for worktrees. Some features may not work as expected."
            )

        # Restore window geometry and last repo
        self._restore_settings()
        
    def _setup_ui(self):
        """Setup the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(6)
        
        # Top bar
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        
        repo_label = QLabel("Repository:")
        top_layout.addWidget(repo_label)
        
        self.repo_combo = QComboBox()
        self.repo_combo.setEditable(True)
        self.repo_combo.setMinimumWidth(400)
        self.repo_combo.addItems(self.cfg.get("recent_repos", []))
        self.repo_combo.currentTextChanged.connect(self._on_repo_combo_changed)
        top_layout.addWidget(self.repo_combo, 1)  # stretch factor 1
        
        # Setup clipboard functionality for repository entry
        setup_entry_clipboard(self.repo_combo.lineEdit())
        add_tooltip(self.repo_combo,
                   "Enter or select a Git repository path.\n"
                   "Recent repositories are shown in dropdown.\n"
                   "Supports clipboard paste (Ctrl+V).")
        
        pick_btn = QPushButton("Pick…")
        pick_btn.clicked.connect(self.choose_repo)
        top_layout.addWidget(pick_btn)
        add_tooltip_to_button(pick_btn, "Browse for a Git repository folder")
        
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self.open_repo_from_entry)
        top_layout.addWidget(open_btn)
        add_tooltip_to_button(open_btn, "Open the repository entered above")
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        top_layout.addWidget(refresh_btn)
        add_tooltip_to_button(refresh_btn, "Refresh worktree list and status (F5)")
        
        self.auto_reopen_cb = QCheckBox("Auto‑reopen last")
        self.auto_reopen_cb.setChecked(bool(self.cfg.get("auto_reopen_last", True)))
        self.auto_reopen_cb.toggled.connect(self._persist_auto_reopen)
        top_layout.addWidget(self.auto_reopen_cb)
        add_tooltip(self.auto_reopen_cb, "Automatically reopen the last used repository when starting the application")
        
        main_layout.addLayout(top_layout)
        
        # Splitter (sidebar + terminal)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Simple worktree sidebar
        self.sidebar = SimpleWorktreeSidebar(
            splitter,
            on_worktree_select=self._on_sidebar_select,
            get_repo_root=lambda: self.repo_root,
            get_branches=self._get_branches
        )
        self.sidebar.set_config(self.cfg)  # Pass config for recent branches tracking
        splitter.addWidget(self.sidebar)
        
        # Right: terminal pane
        self.term = TerminalPane(
            splitter,
            get_selected_cwd=lambda: self.sidebar.get_selected_worktree(),
            claude_cmd_getter=lambda: get_agent_command(self.cfg),
            config_getter=lambda: self.cfg
        )
        splitter.addWidget(self.term)
        
        # Set the session manager for the terminal pane
        self.term.set_session_manager(self.session_manager)
        
        # Update terminal button text with default agent
        self.term.update_run_button_text()
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        main_layout.addWidget(splitter, 1)  # stretch factor 1
        
        # Bottom action bar
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(6)
        
        create_btn = QPushButton("Create worktree")
        create_btn.clicked.connect(self.create_worktree)
        bottom_layout.addWidget(create_btn)
        add_tooltip_to_button(create_btn, "Create a new Git worktree (Ctrl+N)")
        
        remove_btn = QPushButton("Remove worktree")
        remove_btn.clicked.connect(self.remove_selected)
        bottom_layout.addWidget(remove_btn)
        add_tooltip_to_button(remove_btn, "Remove the selected worktree\n(Cannot remove the main worktree)")
        
        prune_btn = QPushButton("Prune stale")
        prune_btn.clicked.connect(self.prune)
        bottom_layout.addWidget(prune_btn)
        add_tooltip_to_button(prune_btn, "Clean up metadata for deleted worktrees")
        
        bottom_layout.addSpacing(20)  # Visual separator
        
        editor_btn = QPushButton("Open in editor")
        editor_btn.clicked.connect(self.open_editor)
        bottom_layout.addWidget(editor_btn)
        add_tooltip_to_button(editor_btn, "Open the selected worktree in your default code editor")
        
        # Agent selector and Run button
        agent_layout = QHBoxLayout()
        
        self.agent_combo = QComboBox()
        self.agent_combo.setMinimumWidth(120)
        self.agent_combo.currentIndexChanged.connect(self._on_agent_selection_changed)
        agent_layout.addWidget(self.agent_combo)
        add_tooltip(self.agent_combo, "Select the coding agent to run")
        
        claude_btn = QPushButton("Run")
        claude_btn.clicked.connect(self.launch_claude)
        agent_layout.addWidget(claude_btn)
        add_tooltip_to_button(claude_btn, "Launch the selected coding agent in the selected worktree")
        
        bottom_layout.addLayout(agent_layout)
        
        bottom_layout.addStretch()
        main_layout.addLayout(bottom_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        status_label = QLabel("Ready")
        status_label.setStyleSheet("color: #9aa1b2; padding: 6px 12px;")
        self.status_bar.addWidget(status_label)
        self.status_label = status_label
        
        # Status tooltip for additional information
        self.status_tooltip = StatusTooltip(status_label)
        
        
    def _play_notification_sound(self):
        try:
            if self._notif_sound and self._notif_sound.source():
                import time
                now = time.time()
                # Rate-limit to avoid rapid repeats
                if (now - self._last_sound_time) >= 4.0:
                    self._notif_sound.play()
                    self._last_sound_time = now
        except Exception:
            pass

    def notify_inactivity(self, path: Path):
        """Called when a background terminal session becomes inactive.
        Shows a subtle indicator on the sidebar if the worktree is not selected.
        """
        try:
            selected = self.sidebar.get_selected_worktree()
            if not selected or selected != path:
                self.sidebar.set_attention_for_path(path, True)
                self._play_notification_sound()
        except Exception:
            pass

    def notify_activity(self, path: Path):
        """Called when a session shows activity; clears the sidebar indicator."""
        try:
            self.sidebar.set_attention_for_path(path, False)
        except Exception:
            pass
    
    def _setup_menus(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open repository…", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.choose_repo)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Recent Repositories submenu
        self.recent_menu = file_menu.addMenu("Recent Repositories")
        self._rebuild_recent_menu()
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.refresh)
        view_menu.addAction(refresh_action)
        
        view_menu.addSeparator()
        
        dark_action = QAction("Dark theme", self)
        dark_action.triggered.connect(lambda: self._switch_theme("dark"))
        view_menu.addAction(dark_action)
        
        light_action = QAction("Light theme", self)
        light_action.triggered.connect(lambda: self._switch_theme("light"))
        view_menu.addAction(light_action)
        
        # Preferences menu
        pref_menu = menubar.addMenu("Preferences")
        
        preferences_action = QAction("Preferences…", self)
        preferences_action.triggered.connect(self._open_preferences)
        pref_menu.addAction(preferences_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # These are in addition to menu shortcuts
        create_shortcut = QKeySequence("Ctrl+N")
        refresh_shortcut = QKeySequence("Ctrl+R")
        
        # Note: Menu actions already have their shortcuts, these are additional
        self.create_worktree  # Will be triggered by menu action
        self.refresh  # Will be triggered by menu action
    
    def _rebuild_recent_menu(self):
        """Rebuild the recent repositories menu."""
        self.recent_menu.clear()
        recents = self.cfg.get("recent_repos", [])
        if not recents:
            empty_action = QAction("(Empty)", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
            return
        
        for path in recents:
            action = QAction(path, self)
            action.triggered.connect(lambda checked, p=path: self._open_repo_by_path(p))
            self.recent_menu.addAction(action)
        
        self.recent_menu.addSeparator()
        clear_action = QAction("Clear history", self)
        clear_action.triggered.connect(self._clear_recents)
        self.recent_menu.addAction(clear_action)
    
    def _apply_theme(self, mode: str = "dark"):
        """Apply theme styling."""
        if mode == "dark":
            # Dark theme colors
            bg = "#0f1115"
            panel = "#151823"
            surface = "#1a1f2e"
            text = "#e6e7ee"
            subtext = "#9aa1b2"
            accent = "#7c7fff"
            sel_bg = "#26304a"
            hover = "#20273a"
            
            style = f"""
                QMainWindow {{
                    background-color: {bg};
                    color: {text};
                }}
                QWidget {{
                    background-color: {bg};
                    color: {text};
                }}
                QLabel {{
                    color: {text};
                    background-color: transparent;
                }}
                QPushButton {{
                    background-color: {surface};
                    color: {text};
                    border: 1px solid #404757;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {hover};
                }}
                QPushButton:pressed {{
                    background-color: {sel_bg};
                }}
                QComboBox {{
                    background-color: {panel};
                    color: {text};
                    border: 1px solid #404757;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 11px;
                }}
                QComboBox:focus {{
                    border: 2px solid {accent};
                }}
                QComboBox::drop-down {{
                    border: none;
                    background-color: {surface};
                }}
                QComboBox QAbstractItemView {{
                    background-color: {panel};
                    color: {text};
                    selection-background-color: {accent};
                    border: 1px solid #404757;
                }}
                QCheckBox {{
                    color: {text};
                    background-color: transparent;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    background-color: {panel};
                    border: 1px solid #404757;
                    border-radius: 3px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {accent};
                    border-color: {accent};
                }}
                QStatusBar {{
                    background-color: {surface};
                    color: {subtext};
                    border-top: 1px solid #404757;
                }}
                QMenuBar {{
                    background-color: {bg};
                    color: {text};
                    border-bottom: 1px solid #404757;
                }}
                QMenuBar::item {{
                    background-color: transparent;
                    padding: 4px 8px;
                }}
                QMenuBar::item:selected {{
                    background-color: {hover};
                }}
                QMenu {{
                    background-color: {panel};
                    color: {text};
                    border: 1px solid #404757;
                }}
                QMenu::item {{
                    padding: 6px 20px;
                }}
                QMenu::item:selected {{
                    background-color: {accent};
                    color: #ffffff;
                }}
                QMenu::separator {{
                    height: 1px;
                    background-color: #404757;
                    margin: 2px 0;
                }}
                QSplitter::handle {{
                    background-color: #404757;
                    width: 2px;
                    height: 2px;
                }}
                QSplitter::handle:hover {{
                    background-color: {accent};
                }}
            """
        else:
            # Light theme colors
            bg = "#f5f6fb"
            panel = "#ffffff"
            surface = "#f0f2f7"
            text = "#0e1116"
            subtext = "#475569"
            accent = "#4f46e5"
            sel_bg = "#e5e7f9"
            hover = "#eceffe"
            
            style = f"""
                QMainWindow {{
                    background-color: {bg};
                    color: {text};
                }}
                QWidget {{
                    background-color: {bg};
                    color: {text};
                }}
                QLabel {{
                    color: {text};
                    background-color: transparent;
                }}
                QPushButton {{
                    background-color: {surface};
                    color: {text};
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {hover};
                }}
                QPushButton:pressed {{
                    background-color: {sel_bg};
                }}
                QComboBox {{
                    background-color: {panel};
                    color: {text};
                    border: 1px solid #d1d5db;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 11px;
                }}
                QComboBox:focus {{
                    border: 2px solid {accent};
                }}
                QComboBox::drop-down {{
                    border: none;
                    background-color: {surface};
                }}
                QComboBox QAbstractItemView {{
                    background-color: {panel};
                    color: {text};
                    selection-background-color: {accent};
                    selection-color: #ffffff;
                    border: 1px solid #d1d5db;
                }}
                QCheckBox {{
                    color: {text};
                    background-color: transparent;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    background-color: {panel};
                    border: 1px solid #d1d5db;
                    border-radius: 3px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {accent};
                    border-color: {accent};
                }}
                QStatusBar {{
                    background-color: {surface};
                    color: {subtext};
                    border-top: 1px solid #d1d5db;
                }}
                QMenuBar {{
                    background-color: {bg};
                    color: {text};
                    border-bottom: 1px solid #d1d5db;
                }}
                QMenuBar::item {{
                    background-color: transparent;
                    padding: 4px 8px;
                }}
                QMenuBar::item:selected {{
                    background-color: {hover};
                }}
                QMenu {{
                    background-color: {panel};
                    color: {text};
                    border: 1px solid #d1d5db;
                }}
                QMenu::item {{
                    padding: 6px 20px;
                }}
                QMenu::item:selected {{
                    background-color: {accent};
                    color: #ffffff;
                }}
                QMenu::separator {{
                    height: 1px;
                    background-color: #d1d5db;
                    margin: 2px 0;
                }}
                QSplitter::handle {{
                    background-color: #d1d5db;
                    width: 2px;
                    height: 2px;
                }}
                QSplitter::handle:hover {{
                    background-color: {accent};
                }}
            """
        
        self.setStyleSheet(style)
        self.cfg["theme"] = mode
        save_config(self.cfg)
    
    def _switch_theme(self, mode: str):
        """Switch to specified theme."""
        self._apply_theme(mode)
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About",
            "Worktree Manager for Claude Code — v2\n"
            "• Multi-session terminal support\n"
            "• Recents + auto‑reopen\n"
            "• Modern dark UI\n"
            "• Embedded terminal via xterm on Linux\n"
            "Built with PySide6 for cross-platform compatibility."
        )
    
    def _restore_settings(self):
        """Restore window geometry and last repo."""
        geom = self.cfg.get("window_geometry")
        if geom:
            try:
                # Parse geometry string (e.g., "1000x600+100+100")
                if 'x' in geom and '+' in geom:
                    size_part, pos_part = geom.split('+', 1)
                    width, height = map(int, size_part.split('x'))
                    x, y = map(int, pos_part.split('+'))
                    self.resize(width, height)
                    self.move(x, y)
            except Exception:
                pass
        
        if self.cfg.get("auto_reopen_last") and self.cfg.get("last_repo"):
            last = Path(self.cfg["last_repo"])
            if last.exists():
                self.repo_root = ensure_repo_root(last)
                self.repo_combo.setCurrentText(str(self.repo_root))
                self._on_repo_opened(self.repo_root)
                self.refresh()
    
    def _on_repo_combo_changed(self, text):
        """Handle repository combo box text changes."""
        # This is called when user types or selects from dropdown
        pass
    
    def choose_repo(self):
        """Choose repository using file dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Choose a Git repository")
        if not folder:
            return
        self._open_repo_by_path(folder)

    def open_repo_from_entry(self):
        """Open repository from current combo box text."""
        val = self.repo_combo.currentText().strip()
        if val:
            self._open_repo_by_path(val)

    def _open_repo_by_path(self, path_str: str):
        """Open repository by path string."""
        try:
            self.repo_root = ensure_repo_root(Path(path_str))
        except Exception as e:
            QMessageBox.critical(self, "Not a Git repository", str(e))
            return
        self.repo_combo.setCurrentText(str(self.repo_root))
        self._on_repo_opened(self.repo_root)
        self.refresh()

    def _on_repo_opened(self, repo_root: Path):
        """Handle repository opened."""
        push_recent_repo(self.cfg, repo_root)
        save_config(self.cfg)
        # Update recents UI
        self.repo_combo.clear()
        self.repo_combo.addItems(self.cfg.get("recent_repos", []))
        self.repo_combo.setCurrentText(str(repo_root))
        self._rebuild_recent_menu()
        self._set_status(f"📂 Repository opened: {repo_root.name}")
        self.status_tooltip.show_message(f"Repository: {repo_root}", "success")

    def refresh(self):
        """Refresh worktree list."""
        repo = self.get_repo()
        if not repo:
            return
        try:
            self.infos = list_worktrees(repo)
        except Exception as e:
            QMessageBox.critical(self, "Error listing worktrees", str(e))
            return

        # Clean up terminated sessions before updating UI
        self.session_manager.cleanup_terminated_sessions()

        self.sidebar.update_worktrees(self.infos)

    def _get_branches(self) -> list[str]:
        """Get list of all branches for branch switching."""
        if not self.repo_root:
            return []
        try:
            return list_branches(self.repo_root)
        except Exception:
            return []

    def _on_sidebar_select(self, worktree_info: WorktreeInfo):
        """Called when a worktree is selected in the sidebar."""
        branch_name = worktree_info.branch.replace("refs/heads/", "") if worktree_info.branch else "detached"
        self._set_status(f"🗂️ Selected: {worktree_info.path.name} (branch: {branch_name})")

        # Switch terminal pane to show this worktree's session
        if self.cfg.get("embed_terminal", True) and self.term.can_embed:
            self.term.switch_to_worktree(worktree_info.path)

    def get_repo(self) -> Path | None:
        """Get current repository."""
        if self.repo_root:
            return self.repo_root
        val = self.repo_combo.currentText().strip()
        if val:
            try:
                self.repo_root = ensure_repo_root(Path(val))
                return self.repo_root
            except Exception:
                pass
        QMessageBox.critical(self, "Select a repository", "Please choose a Git repository.")
        return None

    def selected_worktree(self) -> Path | None:
        """Get selected worktree path."""
        selected = self.sidebar.get_selected_worktree()
        if not selected:
            QMessageBox.critical(self, "No selection", "Please select a worktree in the sidebar.")
            return None
        return selected

    def create_worktree(self):
        """Create a new worktree."""
        repo = self.get_repo()
        if not repo:
            return
        dlg = CreateDialog(self, repo)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result:
            path, branch, base = dlg.result
            try:
                add_worktree(repo, path, branch, base)
                self.refresh()
                self._set_status(f"✅ Created worktree: {path.name}")
                QMessageBox.information(self, "Success", f"Created worktree at {path}")
            except Exception as e:
                QMessageBox.critical(self, "Failed to create worktree", str(e))

    def remove_selected(self):
        """Remove selected worktree."""
        repo = self.get_repo()
        if not repo:
            return
        wt = self.selected_worktree()
        if not wt:
            return
        if wt.resolve() == repo.resolve():
            QMessageBox.critical(self, "Cannot remove main worktree", "You cannot remove the main worktree.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm remove",
            f"Remove worktree at:\n{wt}\n\nOnly clean worktrees can be removed.\nUse force?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            use_force = True
        else:
            return
            
        try:
            # Remove any active session for this worktree
            self.session_manager.remove_session(wt)
            # Remove the worktree
            remove_worktree(repo, wt, force=use_force)
            self.refresh()
            self._set_status(f"🗑️ Removed worktree: {wt.name}")
            QMessageBox.information(self, "Removed", f"Removed worktree at {wt}")
        except Exception as e:
            QMessageBox.critical(self, "Failed to remove", str(e))

    def prune(self):
        """Prune stale worktrees."""
        repo = self.get_repo()
        if not repo:
            return
        try:
            prune_worktrees(repo)
            self.refresh()
            self._set_status("🧹 Pruned stale worktree metadata")
            QMessageBox.information(self, "Pruned", "Pruned stale worktrees metadata.")
        except Exception as e:
            QMessageBox.critical(self, "Failed to prune", str(e))

    def open_editor(self):
        """Open selected worktree in editor."""
        wt = self.selected_worktree()
        if not wt:
            return
        open_in_editor(wt)

    def launch_claude(self):
        """Launch selected agent in selected worktree."""
        wt = self.selected_worktree()
        if not wt:
            return
        
        # Get selected agent
        selected_agent = self.agent_combo.currentData()
        if not selected_agent:
            selected_agent = get_default_agent(self.cfg)
        
        # Get the command for the selected agent
        agent_command = get_agent_command(self.cfg, selected_agent)
        
        # If user prefers embedding and platform supports it, use the right pane
        if self.cfg.get("embed_terminal", True) and self.term.can_embed:
            self.term.run_claude_here(agent_command)
        else:
            launch_claude_in_terminal(wt, claude_cmd=agent_command)

    def _persist_auto_reopen(self, checked: bool):
        """Persist auto-reopen setting."""
        self.cfg["auto_reopen_last"] = checked
        save_config(self.cfg)


    def _open_preferences(self):
        """Open preferences dialog."""
        from .dialogs import AgentConfigDialog
        dialog = AgentConfigDialog(self, self.cfg)
        if dialog.exec() == QDialog.Accepted:
            save_config(self.cfg)
            self._set_status("⚙️ Preferences updated")
            self._populate_agent_combo()  # Refresh agent list
            self.term.update_run_button_text()  # Update terminal button text

    def _clear_recents(self):
        """Clear recent repositories."""
        self.cfg["recent_repos"] = []
        save_config(self.cfg)
        self.repo_combo.clear()
        self._rebuild_recent_menu()
    
    def _populate_agent_combo(self):
        """Populate the agent selector combo box."""
        current_selection = self.agent_combo.currentData()
        self.agent_combo.clear()
        
        agents = get_coding_agents(self.cfg)
        default_agent = get_default_agent(self.cfg)
        
        # Add enabled agents
        for agent_id, agent_config in agents.items():
            if agent_config.get("enabled", True):
                name = agent_config.get("name", agent_id)
                self.agent_combo.addItem(name, agent_id)
        
        # Set default selection
        if current_selection:
            # Try to restore previous selection
            for i in range(self.agent_combo.count()):
                if self.agent_combo.itemData(i) == current_selection:
                    self.agent_combo.setCurrentIndex(i)
                    return
        
        # Fall back to default agent
        for i in range(self.agent_combo.count()):
            if self.agent_combo.itemData(i) == default_agent:
                self.agent_combo.setCurrentIndex(i)
                return
    
    def _on_agent_selection_changed(self, index):
        """Handle agent selection change."""
        if index >= 0:
            agent_id = self.agent_combo.itemData(index)
            agent_name = self.agent_combo.itemText(index)
            self._set_status(f"🤖 Selected agent: {agent_name}")
            # Update terminal button if this becomes the default
            if agent_id == get_default_agent(self.cfg):
                self.term.update_run_button_text()

    def _set_status(self, text: str):
        """Set status bar text."""
        self.status_label.setText(text)

    def closeEvent(self, event):
        """Handle close event."""
        try:
            # Save window geometry
            geometry = self.geometry()
            geom_str = f"{geometry.width()}x{geometry.height()}+{geometry.x()}+{geometry.y()}"
            self.cfg["window_geometry"] = geom_str
            if self.repo_root:
                self.cfg["last_repo"] = str(self.repo_root)
            save_config(self.cfg)
        except Exception:
            pass
        
        # Clean up all terminal sessions
        try:
            self.term.cleanup_all_sessions()
        except Exception:
            pass
        
        event.accept()
