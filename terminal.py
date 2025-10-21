"""Terminal and editor operations for Worktree Manager."""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QMessageBox

from platform_utils import TerminalLauncher


def open_in_editor(path: Path):
    """Try to open path in VS Code (code), fall back to OS default."""
    if shutil.which("code"):
        subprocess.Popen(["code", str(path)])
        return
    # Other popular forks (best-effort)
    for editor in ("cursor", "windsurf", "codium"):
        if shutil.which(editor):
            subprocess.Popen([editor, str(path)])
            return
    # Fall back to OS handler
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def launch_claude_in_terminal(cwd: Path, claude_cmd: str = "claude"):
    """Open a new terminal window and run `claude` in cwd."""
    if not TerminalLauncher.launch(cwd, claude_cmd):
        QMessageBox.critical(None, "Error", "No supported terminal emulator found.")


def launch_terminal_only(cwd: Path):
    """Open a new terminal window in cwd without running claude."""
    if not TerminalLauncher.launch(cwd):
        QMessageBox.critical(None, "Error", "No supported terminal emulator found.")

