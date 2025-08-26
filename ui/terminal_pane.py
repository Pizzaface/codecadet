"""Terminal pane UI component."""

import os
import sys
import shlex
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QMessageBox
)

from git_utils import which
from terminal import launch_claude_in_terminal, launch_terminal_only


class TerminalPane(QWidget):
    """
    Multi-session terminal pane that maintains separate xterm sessions for each worktree.
    Shows/hides the appropriate session when switching worktrees.
    """

    def __init__(self, parent, get_selected_cwd, claude_cmd_getter):
        super().__init__(parent)
        self.get_selected_cwd = get_selected_cwd
        self.get_claude_cmd = claude_cmd_getter
        self.current_worktree_path: Path | None = None
        self.current_container: QWidget | None = None

        # Get session manager from the App instance
        self.session_manager = None  # Will be set by App

        self._setup_ui()
        self._apply_dark_theme()

    def _setup_ui(self):
        """Setup the terminal pane UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Top bar
        bar_layout = QHBoxLayout()
        
        title_label = QLabel("Terminal")
        bar_layout.addWidget(title_label)
        
        bar_layout.addStretch()
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #8b8e98;")
        bar_layout.addWidget(self.status_lbl)
        
        layout.addLayout(bar_layout)
        
        # Main container for terminal sessions
        self.main_container = QWidget()
        self.main_container_layout = QVBoxLayout(self.main_container)
        self.main_container_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.main_container, 1)  # stretch factor 1
        
        # No session frame (shown when no session exists)
        self.no_session_frame = QFrame()
        no_session_layout = QVBoxLayout(self.no_session_frame)
        no_session_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        no_session_label = QLabel("No Session")
        no_session_label.setStyleSheet("""
            QLabel {
                color: #8b8e98;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        no_session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_session_layout.addWidget(no_session_label)
        
        # Control bar
        control_layout = QHBoxLayout()
        
        run_claude_btn = QPushButton("▶ Run Claude here")
        run_claude_btn.clicked.connect(self.run_claude_here)
        control_layout.addWidget(run_claude_btn)
        
        external_btn = QPushButton("□ Open External Terminal")
        external_btn.clicked.connect(self.open_external)
        control_layout.addWidget(external_btn)
        
        control_layout.addStretch()
        
        stop_btn = QPushButton("⛔ Stop")
        stop_btn.clicked.connect(self.stop_current)
        control_layout.addWidget(stop_btn)
        
        layout.addLayout(control_layout)
        
        self._update_embed_status()
        self._show_no_session()

    def _apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #0f1115;
                color: #e6e7ee;
            }
            QLabel {
                color: #e6e7ee;
                font-size: 11px;
            }
            QPushButton {
                background-color: #1a1f2e;
                color: #e6e7ee;
                border: 1px solid #404757;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #20273a;
            }
            QPushButton:pressed {
                background-color: #26304a;
            }
            QFrame {
                background-color: #0f1115;
            }
        """)

    def set_session_manager(self, session_manager):
        """Set the session manager instance."""
        self.session_manager = session_manager

    @property
    def can_embed(self) -> bool:
        return (sys.platform.startswith("linux") and which("xterm") is not None)

    def _update_embed_status(self):
        if self.can_embed:
            self.status_lbl.setText("Multi-session mode (xterm)")
        else:
            self.status_lbl.setText("Embedding not available; using external terminal")

    def _show_no_session(self):
        """Show the 'No Session' frame."""
        # Hide all session containers
        self._hide_all_containers()
        # Show no session frame
        self.main_container_layout.addWidget(self.no_session_frame)
        self.no_session_frame.show()
        self.current_container = None
        self.status_lbl.setText("No active session")

    def _hide_all_containers(self):
        """Hide and remove all child widgets from the main container."""
        while self.main_container_layout.count():
            child = self.main_container_layout.takeAt(0)
            if child.widget():
                child.widget().hide()

    def switch_to_worktree(self, worktree_path: Path):
        """Switch to show the terminal for the given worktree."""
        if not self.can_embed or not self.session_manager:
            return

        self.current_worktree_path = worktree_path

        # Check if there's an active session for this worktree
        session = self.session_manager.get_session(worktree_path)

        if session and session.container_frame:
            # Hide all containers first
            self._hide_all_containers()

            # Show this session's container
            self.main_container_layout.addWidget(session.container_frame)
            session.container_frame.show()
            self.current_container = session.container_frame
            self.status_lbl.setText(f"Active session: {worktree_path.name}")
        else:
            # No session for this worktree
            self._show_no_session()

    def run_claude_here(self):
        """Start a new Claude session for the current worktree."""
        cwd = self.get_selected_cwd()
        if not cwd:
            return

        self.current_worktree_path = cwd

        if not self.can_embed:
            self.open_external()
            return

        # Check if we already have a session for this worktree
        existing_session = self.session_manager.get_session(cwd)
        if existing_session:
            # Session already exists, just switch to it
            self.switch_to_worktree(cwd)
            return

        # Create a new container widget for this session
        container = QWidget(self.main_container)
        container.setStyleSheet("background-color: black;")

        # Hide all containers and show the new one
        self._hide_all_containers()
        self.main_container_layout.addWidget(container)
        container.show()
        self.current_container = container

        # Ensure the container is properly sized and visible
        container.updateGeometry()
        
        # Get the native window ID for embedding
        wid = container.winId()

        # Calculate appropriate geometry
        container_width = container.width() if container.width() > 0 else 800
        container_height = container.height() if container.height() > 0 else 600
        char_width = 7
        char_height = 14
        cols = max(40, (container_width - 20) // char_width)
        rows = max(10, (container_height - 20) // char_height)
        geometry = f"{cols}x{rows}"

        claude_cmd = self.get_claude_cmd()

        # Command that starts in the worktree directory with Poetry available
        # We explicitly preserve PATH and source bashrc for user tools
        # Properly escape the PATH to handle spaces and special characters
        current_path = os.environ.get("PATH", "")
        # Add common Poetry/pyenv paths that might not be in the parent's PATH
        additional_paths = "$HOME/.local/bin:$HOME/.poetry/bin:$HOME/.pyenv/bin:$HOME/.pyenv/shims"
        bash_command = (
            f'source ~/.bashrc 2>/dev/null; '  # Source user's bashrc for any additional setup
            f'export PATH={shlex.quote(current_path)}:{additional_paths}; '  # Import global PATH plus common tool paths
            f'cd {shlex.quote(str(cwd))} && {claude_cmd}; '
            f'cd {shlex.quote(str(cwd))}; '
            f'exec bash -i'  # Interactive shell to maintain environment
        )

        cmdline = [
            "xterm",
            "-into", str(wid),
            "-geometry", geometry,
            "-fa", "Monospace",
            "-fs", "11",
            "-bg", "black",
            "-fg", "white",
            # Enhanced clipboard support
            "+sb",  # Disable scrollbar for cleaner look
            "-xrm", "*VT100.translations: #override \\n" +
                    "Shift Ctrl <Key>V: insert-selection(CLIPBOARD) \\n" +
                    "Shift Ctrl <Key>C: copy-selection(CLIPBOARD) \\n" +
                    "Ctrl <Key>v: insert-selection(CLIPBOARD) \\n" +
                    "Ctrl <Key>c: copy-selection(CLIPBOARD)",
            "-e", "bash", "-c", bash_command
        ]

        try:
            # Pass the parent's full environment to preserve PATH and other variables
            env = os.environ.copy()
            
            # Clear ONLY the virtual environment variables that would confuse Poetry
            # about which project to use, but keep PATH intact
            app_dir = Path(__file__).parent.parent
            if 'VIRTUAL_ENV' in env:
                venv_path = env.get('VIRTUAL_ENV', '')
                if str(app_dir) in venv_path:
                    # This is the Worktree Manager's venv, clear it
                    env.pop('VIRTUAL_ENV', None)
                    env.pop('POETRY_ACTIVE', None)
                    # But do NOT modify PATH - Poetry binary should still be accessible
            
            # Using cwd parameter ensures the process starts in the worktree directory
            proc = subprocess.Popen(cmdline, cwd=str(cwd), env=env)

            # Register this session
            self.session_manager.register_session(
                worktree_path=cwd,
                process=proc,
                container_frame=container,
                command=claude_cmd
            )

            self.status_lbl.setText(f"Started new session: {cwd.name}")

        except Exception as e:
            QMessageBox.critical(self, "Failed to start embedded terminal", str(e))
            container.setParent(None)
            container.deleteLater()
            self._show_no_session()

    def open_external(self):
        """Open an external terminal."""
        cwd = self.get_selected_cwd()
        if not cwd:
            return

        # Ask user if they want Claude or just terminal
        reply = QMessageBox.question(
            self,
            "Terminal Options",
            "Launch with Claude?\n\nYes - Run Claude in terminal\nNo - Just open terminal",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            launch_claude_in_terminal(cwd, claude_cmd=self.get_claude_cmd())
        else:
            launch_terminal_only(cwd)

    def stop_current(self):
        """Stop the current worktree's session."""
        if self.current_worktree_path and self.session_manager:
            self.session_manager.remove_session(self.current_worktree_path)
            self._show_no_session()

    def cleanup_all_sessions(self):
        """Clean up all sessions when closing the app."""
        if self.session_manager:
            for path_str in list(self.session_manager.sessions.keys()):
                self.session_manager.remove_session(Path(path_str))
