"""Cross-platform utilities for shell detection and platform-specific operations."""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional, List, Tuple


class Platform:
    """Centralized platform detection and utilities."""

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return sys.platform.startswith("win")

    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS."""
        return sys.platform == "darwin"

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux."""
        return sys.platform.startswith("linux")

    @staticmethod
    def is_unix() -> bool:
        """Check if running on Unix-like system (Linux or macOS)."""
        return Platform.is_linux() or Platform.is_macos()


class Shell:
    """Shell detection and management."""

    @staticmethod
    def get_user_shell() -> str:
        """
        Detect the user's default shell in a cross-platform way.

        Returns:
            Path to the user's shell executable.
        """
        if Platform.is_windows():
            # On Windows, prefer PowerShell, fall back to cmd
            pwsh = shutil.which("pwsh") or shutil.which("powershell")
            return pwsh or "cmd.exe"

        # On Unix systems, check SHELL environment variable first
        shell_from_env = os.environ.get("SHELL")
        if shell_from_env and os.path.exists(shell_from_env):
            return shell_from_env

        # Try to get shell from password database
        try:
            import pwd
            user_shell = pwd.getpwuid(os.getuid()).pw_shell
            if user_shell and os.path.exists(user_shell):
                return user_shell
        except (ImportError, KeyError):
            pass

        # Fallback: try common shells in order of preference
        common_shells = [
            "/bin/bash",
            "/usr/bin/bash",
            "/bin/sh",
            "/usr/bin/sh",
            "/bin/zsh",
            "/usr/bin/zsh",
        ]

        for shell in common_shells:
            if os.path.exists(shell):
                return shell

        # Last resort
        return "/bin/sh"

    @staticmethod
    def get_shell_args(shell_path: str, command: str) -> List[str]:
        """
        Get appropriate shell arguments for executing a command.

        Args:
            shell_path: Path to the shell executable
            command: Command to execute

        Returns:
            List of arguments for the shell
        """
        shell_name = os.path.basename(shell_path).lower()

        # Windows shells
        if "cmd" in shell_name:
            return [shell_path, "/c", command]
        elif "powershell" in shell_name or "pwsh" in shell_name:
            return [shell_path, "-Command", command]

        # Unix shells (bash, zsh, sh, etc.)
        return [shell_path, "-c", command]


class TerminalLauncher:
    """Cross-platform terminal launcher."""

    # Terminal configurations: (binary_name, args_builder)
    # args_builder is a function that takes (cwd, command) and returns args list
    LINUX_TERMINALS = [
        ("x-terminal-emulator", lambda cwd, cmd: [
            "-e", "bash", "-lc", f'cd "{cwd}" && {cmd}; exec bash'
        ] if cmd else ["-e", "bash", "-lc", f'cd "{cwd}"; exec bash']),
        ("gnome-terminal", lambda cwd, cmd: [
            "--", "bash", "-lc", f'cd "{cwd}" && {cmd}; exec bash'
        ] if cmd else ["--", "bash", "-lc", f'cd "{cwd}"; exec bash']),
        ("konsole", lambda cwd, cmd: [
            "--workdir", str(cwd), "-e", "bash", "-lc", f"{cmd}; exec bash"
        ] if cmd else ["--workdir", str(cwd)]),
        ("xfce4-terminal", lambda cwd, cmd: [
            "--working-directory", str(cwd), "-e", "bash", "-lc", f"{cmd}; exec bash"
        ] if cmd else ["--working-directory", str(cwd)]),
        ("alacritty", lambda cwd, cmd: [
            "--working-directory", str(cwd), "-e", "bash", "-lc", f"{cmd}; exec bash"
        ] if cmd else ["--working-directory", str(cwd), "-e", "bash"]),
        ("kitty", lambda cwd, cmd: [
            "-d", str(cwd), "-e", "sh", "-lc", f"{cmd}; exec sh"
        ] if cmd else ["-d", str(cwd)]),
        ("xterm", lambda cwd, cmd: [
            "-e", "bash", "-lc", f'cd "{cwd}" && {cmd}; exec bash'
        ] if cmd else ["-e", "bash", "-lc", f'cd "{cwd}"; exec bash']),
    ]

    @staticmethod
    def find_available_terminal() -> Optional[Tuple[str, callable]]:
        """
        Find the first available terminal emulator on Linux.

        Returns:
            Tuple of (terminal_path, args_builder) or None if not found
        """
        if not Platform.is_linux():
            return None

        for term_name, args_builder in TerminalLauncher.LINUX_TERMINALS:
            term_path = shutil.which(term_name)
            if term_path:
                return (term_path, args_builder)

        return None

    @staticmethod
    def launch(cwd: Path, command: Optional[str] = None) -> bool:
        """
        Launch a terminal window in the specified directory.

        Args:
            cwd: Working directory for the terminal
            command: Optional command to run in the terminal

        Returns:
            True if terminal was launched successfully, False otherwise
        """
        import subprocess
        import shlex

        cwd = Path(cwd)

        try:
            # Windows
            if Platform.is_windows():
                wt = shutil.which("wt")
                if wt:
                    if command:
                        subprocess.Popen([wt, "new-tab", "cmd", "/k", f'cd /d "{cwd}" && {command}'], cwd=str(cwd))
                    else:
                        subprocess.Popen([wt, "new-tab", "-d", str(cwd)], cwd=str(cwd))
                else:
                    if command:
                        subprocess.Popen(["cmd", "/k", f'cd /d "{cwd}" && {command}'], cwd=str(cwd))
                    else:
                        subprocess.Popen(["cmd", "/k", f'cd /d "{cwd}"'], cwd=str(cwd))
                return True

            # macOS
            if Platform.is_macos():
                if command:
                    osa = f'''
                    tell application "Terminal"
                        activate
                        do script "cd {shlex.quote(str(cwd))} && {command}; cd {shlex.quote(str(cwd))}"
                    end tell
                    '''
                else:
                    osa = f'''
                    tell application "Terminal"
                        activate
                        do script "cd {shlex.quote(str(cwd))}"
                    end tell
                    '''
                subprocess.Popen(["osascript", "-e", osa], cwd=str(cwd))
                return True

            # Linux
            if Platform.is_linux():
                terminal = TerminalLauncher.find_available_terminal()
                if terminal:
                    term_path, args_builder = terminal
                    args = args_builder(str(cwd), command)
                    subprocess.Popen([term_path] + args, cwd=str(cwd))
                    return True

            return False

        except Exception:
            return False
