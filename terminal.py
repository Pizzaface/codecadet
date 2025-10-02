"""Terminal and editor operations for Worktree Manager."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from git_utils import which


def open_in_editor(path: Path):
    """Try to open path in VS Code (code), fall back to OS default."""
    if which("code"):
        subprocess.Popen(["code", str(path)])
        return
    # Other popular forks (best-effort)
    for editor in ("cursor", "windsurf", "codium"):
        if which(editor):
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
    cmd = claude_cmd

    # Windows
    if sys.platform.startswith("win"):
        wt = which("wt")
        if wt:
            subprocess.Popen([wt, "new-tab", "cmd", "/k", f'cd /d "{cwd}" && {cmd}'], cwd=str(cwd))
            return
        subprocess.Popen(["cmd", "/k", f'cd /d "{cwd}" && {cmd}'], cwd=str(cwd))
        return

    # macOS
    if sys.platform == "darwin":
        osa = f"""
        tell application "Terminal"
            activate
            do script "cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}"
        end tell
        """
        subprocess.Popen(["osascript", "-e", osa], cwd=str(cwd))
        return

    # Linux / Unix – try common terminals
    candidates = [
        (
            "x-terminal-emulator",
            [
                "-e",
                "bash",
                "-lc",
                f"cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}; exec bash",
            ],
        ),
        (
            "gnome-terminal",
            [
                "--",
                "bash",
                "-lc",
                f"cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}; exec bash",
            ],
        ),
        (
            "konsole",
            [
                "-e",
                "bash",
                "-lc",
                f"cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}; exec bash",
            ],
        ),
        (
            "xfce4-terminal",
            [
                "-e",
                "bash",
                "-lc",
                f"cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}; exec bash",
            ],
        ),
        (
            "xterm",
            [
                "-e",
                "bash",
                "-lc",
                f"cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}; exec bash",
            ],
        ),
        (
            "alacritty",
            [
                "-e",
                "bash",
                "-lc",
                f"cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}; exec bash",
            ],
        ),
        (
            "kitty",
            [
                "-e",
                "sh",
                "-lc",
                f"cd {shlex.quote(str(cwd))} && {cmd}; cd {shlex.quote(str(cwd))}; exec sh",
            ],
        ),
    ]
    for term, args in candidates:
        if which(term):
            subprocess.Popen([term] + args, cwd=str(cwd))
            return
    # If no terminal found, show error
    QMessageBox.critical(None, "Error", "No supported terminal emulator found.")


def launch_terminal_only(cwd: Path):
    """Open a new terminal window in cwd without running claude."""
    # Windows
    if sys.platform.startswith("win"):
        wt = which("wt")
        if wt:
            subprocess.Popen([wt, "new-tab", "-d", str(cwd)], cwd=str(cwd))
            return
        subprocess.Popen(["cmd", "/k", f'cd /d "{cwd}"'], cwd=str(cwd))
        return

    # macOS
    if sys.platform == "darwin":
        osa = f"""
        tell application "Terminal"
            activate
            do script "cd {shlex.quote(str(cwd))}"
        end tell
        """
        subprocess.Popen(["osascript", "-e", osa], cwd=str(cwd))
        return

    # Linux / Unix – try common terminals
    candidates = [
        ("x-terminal-emulator", ["-e", "bash", "-lc", f"cd {shlex.quote(str(cwd))}; exec bash"]),
        ("gnome-terminal", ["--", "bash", "-lc", f"cd {shlex.quote(str(cwd))}; exec bash"]),
        ("konsole", ["--workdir", str(cwd)]),
        ("xfce4-terminal", ["--working-directory", str(cwd)]),
        ("xterm", ["-e", "bash", "-lc", f"cd {shlex.quote(str(cwd))}; exec bash"]),
        ("alacritty", ["-e", "bash", "-lc", f"cd {shlex.quote(str(cwd))}; exec bash"]),
        ("kitty", ["-d", str(cwd)]),
    ]
    for term, args in candidates:
        if which(term):
            subprocess.Popen([term] + args, cwd=str(cwd))
            return
    # If no terminal found, show error
    QMessageBox.critical(None, "Error", "No supported terminal emulator found.")
