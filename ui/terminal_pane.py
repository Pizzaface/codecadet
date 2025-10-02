"""Terminal pane UI component."""

import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from git_utils import which
from terminal import launch_claude_in_terminal, launch_terminal_only


class TerminalPane(QWidget):
    """
    Multi-session terminal pane that maintains separate xterm sessions for each worktree.
    Shows/hides the appropriate session when switching worktrees.
    """

    @staticmethod
    def _remove_path_entry(path_value: str, entry: str) -> str:
        """Remove all occurrences of `entry` from a PATH-like string."""
        if not path_value or not entry:
            return path_value
        sep = os.pathsep
        parts = path_value.split(sep)
        cleaned = [part for part in parts if part != entry]
        return sep.join(cleaned)

    def __init__(self, parent, get_selected_cwd, claude_cmd_getter, config_getter=None):
        super().__init__(parent)
        self.get_selected_cwd = get_selected_cwd
        self.get_claude_cmd = claude_cmd_getter
        self.get_config = config_getter
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

        self.run_claude_btn = QPushButton("▶ Run Claude here")
        self.run_claude_btn.clicked.connect(self.run_claude_here)
        control_layout.addWidget(self.run_claude_btn)
        self.update_run_button_text()

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

    def update_run_button_text(self):
        """Update the run button text with the default agent name."""
        if self.get_config:
            from config import get_agent_config, get_default_agent

            config = self.get_config()
            default_agent = get_default_agent(config)
            agent_config = get_agent_config(config, default_agent)
            if agent_config:
                agent_name = agent_config.get("name", default_agent)
                self.run_claude_btn.setText(f"▶ Run {agent_name} here")
            else:
                self.run_claude_btn.setText("▶ Run Claude here")
        else:
            self.run_claude_btn.setText("▶ Run Claude here")

    @property
    def can_embed(self) -> bool:
        # Linux: Use xterm embedding
        if sys.platform.startswith("linux"):
            return which("xterm") is not None
        # macOS: Check for iTerm2 first, then Terminal.app
        elif sys.platform == "darwin":
            return True
        return False

    def _update_embed_status(self):
        if self.can_embed:
            if sys.platform == "darwin":
                self.status_lbl.setText("Multi-session mode (PTY)")
            else:
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

    def run_claude_here(self, agent_cmd=None):
        """Start a new agent session for the current worktree."""
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

        claude_cmd = agent_cmd if agent_cmd else self.get_claude_cmd()

        # Command that starts in the worktree directory with common developer environments available
        # We explicitly preserve PATH and source appropriate profile files for user tools
        # Properly escape the PATH to handle spaces and special characters
        # Current PATH is not used directly; we rely on sourced profiles' PATH and append common paths.
        # Common developer tool paths that may not be present depending on how the app was launched
        # (Finder-launched apps often inherit a minimal PATH on macOS)
        additional_paths = ":".join(
            [
                "$HOME/.local/bin",
                "$HOME/.poetry/bin",
                "$HOME/.pyenv/bin",
                "$HOME/.pyenv/shims",
                "$HOME/.asdf/bin",
                "$HOME/.asdf/shims",
                "$HOME/.rtx/bin",
                "$HOME/.deno/bin",
                "$HOME/.cargo/bin",
                "/opt/homebrew/bin",
                "/opt/homebrew/sbin",
                "/usr/local/bin",
                "/usr/local/sbin",
            ]
        )

        app_dir = Path(__file__).parent.parent
        venv_bin_dir = app_dir / ".venv" / ("Scripts" if sys.platform.startswith("win") else "bin")
        app_venv_bin_str = os.fspath(venv_bin_dir)

        path_cleanup_snippet = ""
        if not sys.platform.startswith("win") and app_venv_bin_str:
            escaped_app_venv_bin = (
                app_venv_bin_str.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
            )
            path_cleanup_snippet = (
                f'APP_VENV_BIN="{escaped_app_venv_bin}"; '
                'PATH="$(printf \'%s\' "$PATH" | awk -v RS=: -v ORS=: -v target="$APP_VENV_BIN" \'$0 != target\')"; '
                'PATH="${PATH%:}"; '
                "unset APP_VENV_BIN; "
            )

        path_append_snippet = (
            f'PATH_EXTRAS="{additional_paths}"; '
            'if [ -n "$PATH" ]; then PATH="$PATH:$PATH_EXTRAS"; else PATH="$PATH_EXTRAS"; fi; '
            "unset PATH_EXTRAS; "
        )

        # Choose appropriate shell and profile based on platform
        if sys.platform == "darwin":
            shell_cmd = "zsh"
            # Source all relevant zsh and profile files if present, then ensure Homebrew env if available.
            profile_source = (
                "for f in /etc/zshenv /etc/zprofile /etc/profile ~/.zshenv ~/.zprofile ~/.profile ~/.zshrc; "
                'do [ -f "$f" ] && . "$f"; done; '
                "eval \"$('/opt/homebrew/bin/brew' shellenv)\" 2>/dev/null || "
                "eval \"$('/usr/local/bin/brew' shellenv)\" 2>/dev/null || true"
            )
        else:
            shell_cmd = "bash"
            # Source common bash profile files on Linux; cover login and non-login shells.
            profile_source = (
                "for f in /etc/profile ~/.bash_profile ~/.bash_login ~/.profile ~/.bashrc; "
                'do [ -f "$f" ] && . "$f"; done'
            )

        bash_command = (
            f"{path_cleanup_snippet}"
            f"{profile_source}; "  # Source user/system profiles for environment setup
            f"{path_cleanup_snippet}"
            f"{path_append_snippet}"  # Extend PATH with common tool locations, preserving profile changes
            f"export LANG=en_US.UTF-8; "  # Ensure UTF-8 locale
            f"export LC_ALL=en_US.UTF-8; "  # Force UTF-8 for all categories
            f"export LC_CTYPE=en_US.UTF-8; "  # Character classification
            f"export PYTHONIOENCODING=utf-8; "  # Python UTF-8 handling
            f"cd {shlex.quote(str(cwd))} && {claude_cmd}; "
            f"cd {shlex.quote(str(cwd))}; "
            f"exec {shell_cmd} -i"  # Interactive shell to maintain environment
        )

        # Platform-specific terminal implementation
        if sys.platform == "darwin":
            # Mac: Use PTY-based terminal emulator
            self._start_pty_terminal(container, cwd, bash_command, claude_cmd)
        else:
            # Linux: Use xterm embedding
            self._start_xterm_terminal(
                container, cwd, bash_command, claude_cmd, geometry, wid, app_venv_bin_str
            )

    def _start_pty_terminal(self, container, cwd, bash_command, claude_cmd):
        """Start a PTY-based terminal for Mac."""
        try:
            # Try web terminal first (better character handling)
            try:
                from .web_terminal import WebTerminalWidget

                # Create web terminal widget
                terminal_widget = WebTerminalWidget(container, bash_command, str(cwd))
                # Hook inactivity signal to bubble up to the main app/sidebar
                try:
                    terminal_widget.inactivity_for_worktree.connect(self._on_session_inactivity)
                    terminal_widget.activity_for_worktree.connect(self._on_session_activity)
                except (AttributeError, RuntimeError) as e:
                    logging.debug(f"Failed to connect terminal widget signals: {e}")
                    pass

                # Add to container layout
                layout = QVBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(terminal_widget)

                # Create a mock process object for compatibility with session manager
                class MockProcess:
                    def __init__(self, widget):
                        self.widget = widget

                    def poll(self):
                        # Check if process is still running via bridge
                        if hasattr(self.widget, "bridge") and hasattr(
                            self.widget.bridge, "process_pid"
                        ):
                            try:
                                os.kill(self.widget.bridge.process_pid, 0)
                                return None  # Still running
                            except OSError:
                                return 0  # Process ended
                        return 0

                    def terminate(self):
                        if hasattr(self.widget, "cleanup"):
                            self.widget.cleanup()

                # Register this session with mock process
                self.session_manager.register_session(
                    worktree_path=cwd,
                    process=MockProcess(terminal_widget),
                    container_frame=container,
                    command=claude_cmd,
                )

                self.status_lbl.setText(f"Started web terminal session: {cwd.name}")
                return

            except ImportError:
                # Fall back to original PTY terminal
                from .pty_terminal import PTYTerminalWidget

                # Create PTY terminal widget
                terminal_widget = PTYTerminalWidget(container, bash_command, str(cwd))

                # Add to container layout
                layout = QVBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(terminal_widget)

                # Create a mock process object for compatibility with session manager
                class MockProcess:
                    def __init__(self, widget):
                        self.widget = widget

                    def poll(self):
                        # Check if process is still running
                        if hasattr(self.widget, "process_pid"):
                            try:
                                os.kill(self.widget.process_pid, 0)
                                return None  # Still running
                            except OSError:
                                return 0  # Process ended
                        return 0

                    def terminate(self):
                        if hasattr(self.widget, "_cleanup"):
                            self.widget._cleanup()

                # Register this session with mock process
                self.session_manager.register_session(
                    worktree_path=cwd,
                    process=MockProcess(terminal_widget),
                    container_frame=container,
                    command=claude_cmd,
                )

                self.status_lbl.setText(f"Started PTY terminal session: {cwd.name}")

        except ImportError as e:
            # Fallback to external terminal if no terminal widget available
            QMessageBox.information(
                self,
                "Terminal",
                f"Embedded terminal not available: {e}. Opening external terminal.",
            )
            self.open_external()
            container.setParent(None)
            container.deleteLater()
            self._show_no_session()
        except Exception as e:
            QMessageBox.critical(self, "Failed to start embedded terminal", str(e))
            container.setParent(None)
            container.deleteLater()
            self._show_no_session()

    def _start_xterm_terminal(
        self, container, cwd, bash_command, claude_cmd, geometry, wid, app_venv_bin=None
    ):
        """Start xterm-based terminal for Linux."""
        cmdline = [
            "xterm",
            "-into",
            str(wid),
            "-geometry",
            geometry,
            "-fa",
            "Monospace",
            "-fs",
            "11",
            "-bg",
            "black",
            "-fg",
            "white",
            # Enhanced clipboard support
            "+sb",  # Disable scrollbar for cleaner look
            "-xrm",
            "*VT100.translations: #override \\n"
            + "Shift Ctrl <Key>V: insert-selection(CLIPBOARD) \\n"
            + "Shift Ctrl <Key>C: copy-selection(CLIPBOARD) \\n"
            + "Ctrl <Key>v: insert-selection(CLIPBOARD) \\n"
            + "Ctrl <Key>c: copy-selection(CLIPBOARD)",
            "-e",
            "bash",
            "-c",
            bash_command,
        ]

        try:
            # Pass the parent's full environment to preserve PATH and other variables
            env = os.environ.copy()

            # Clear ONLY the virtual environment variables that would confuse Poetry
            # about which project to use, but keep PATH intact
            app_dir = Path(__file__).parent.parent
            if "VIRTUAL_ENV" in env:
                venv_path = env.get("VIRTUAL_ENV", "")
                if str(app_dir) in venv_path:
                    # This is the Worktree Manager's venv, clear it
                    env.pop("VIRTUAL_ENV", None)
                    env.pop("POETRY_ACTIVE", None)
                    # But do NOT modify PATH - Poetry binary should still be accessible

            if app_venv_bin:
                env_path = env.get("PATH")
                if env_path:
                    cleaned_path = self._remove_path_entry(env_path, app_venv_bin)
                    if cleaned_path:
                        env["PATH"] = cleaned_path
                    else:
                        env["PATH"] = os.defpath

            # Using cwd parameter ensures the process starts in the worktree directory
            proc = subprocess.Popen(cmdline, cwd=str(cwd), env=env)

            # Register this session
            self.session_manager.register_session(
                worktree_path=cwd, process=proc, container_frame=container, command=claude_cmd
            )

            self.status_lbl.setText(f"Started new session: {cwd.name}")

        except Exception as e:
            QMessageBox.critical(self, "Failed to start embedded terminal", str(e))
            container.setParent(None)
            container.deleteLater()
            self._show_no_session()

    def _get_main_app(self):
        widget = self
        while widget:
            if hasattr(widget, "notify_inactivity") and hasattr(widget, "sidebar"):
                return widget
            widget = widget.parent()
        return None

    def _on_session_inactivity(self, path_str: str):
        """Receive inactivity from a terminal session and notify the app/sidebar."""
        try:
            from pathlib import Path

            session_path = Path(path_str)
            # Always notify the app so it can handle sound and indicators appropriately
            app = self._get_main_app()
            if app and hasattr(app, "notify_inactivity"):
                app.notify_inactivity(session_path)
        except (AttributeError, RuntimeError) as e:
            logging.warning(f"Failed to notify inactivity for session {path_str}: {e}")
            pass

    def _on_session_activity(self, path_str: str):
        """Clear sidebar attention when session shows activity again."""
        try:
            from pathlib import Path

            app = self._get_main_app()
            if app and hasattr(app, "notify_activity"):
                app.notify_activity(Path(path_str))
        except (AttributeError, RuntimeError) as e:
            logging.warning(f"Failed to notify activity for session {path_str}: {e}")
            pass

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
            QMessageBox.StandardButton.Yes,
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
