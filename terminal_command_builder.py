"""Terminal command builder for launching agents in terminal sessions.

This module encapsulates the complex logic of building shell commands
for different platforms and terminal types, following the Single
Responsibility Principle.
"""

import sys
import shlex
from pathlib import Path
from typing import Optional

from constants import (
    COMMON_DEVELOPER_PATHS,
    DEFAULT_LOCALE,
    ENV_VAR_LANG,
    ENV_VAR_LC_ALL,
    ENV_VAR_LC_CTYPE,
    ENV_VAR_PYTHONIOENCODING
)


class TerminalCommandBuilder:
    """Builder for constructing terminal launch commands.

    This class handles the complexity of building platform-specific
    shell commands with proper environment setup.
    """

    def __init__(self, platform: Optional[str] = None):
        """Initialize command builder.

        Args:
            platform: Platform identifier (default: sys.platform)
        """
        self.platform = platform or sys.platform
        self._app_venv_bin: Optional[str] = None

    def set_app_venv_bin(self, venv_bin_path: Path) -> None:
        """Set the application's virtual environment bin directory to exclude.

        Args:
            venv_bin_path: Path to the app's venv bin directory
        """
        self._app_venv_bin = str(venv_bin_path)

    def _build_path_cleanup_snippet(self) -> str:
        """Build bash snippet to remove app venv from PATH.

        Returns:
            Bash code snippet or empty string
        """
        if self.platform.startswith("win") or not self._app_venv_bin:
            return ""

        # Escape the path for safe use in bash
        escaped_path = (
            self._app_venv_bin
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("$", "\\$")
        )

        return (
            f'APP_VENV_BIN="{escaped_path}"; '
            'PATH="$(printf \'%s\' "$PATH" | awk -v RS=: -v ORS=: -v target="$APP_VENV_BIN" \'$0 != target\')"; '
            'PATH="${PATH%:}"; '
            'unset APP_VENV_BIN; '
        )

    def _build_path_append_snippet(self) -> str:
        """Build bash snippet to append common developer paths to PATH.

        Returns:
            Bash code snippet
        """
        additional_paths = ":".join(COMMON_DEVELOPER_PATHS)

        return (
            f'PATH_EXTRAS="{additional_paths}"; '
            'if [ -n "$PATH" ]; then PATH="$PATH:$PATH_EXTRAS"; else PATH="$PATH_EXTRAS"; fi; '
            'unset PATH_EXTRAS; '
        )

    def _build_profile_source_snippet(self) -> str:
        """Build bash snippet to source shell profile files.

        Returns:
            Bash code snippet for sourcing profile files
        """
        if self.platform == "darwin":
            # macOS: Source zsh profiles and Homebrew environment
            return (
                "for f in /etc/zshenv /etc/zprofile /etc/profile ~/.zshenv ~/.zprofile ~/.profile ~/.zshrc; "
                "do [ -f \"$f\" ] && . \"$f\"; done; "
                "eval \"$('/opt/homebrew/bin/brew' shellenv)\" 2>/dev/null || "
                "eval \"$('/usr/local/bin/brew' shellenv)\" 2>/dev/null || true"
            )
        else:
            # Linux: Source bash profiles
            return (
                "for f in /etc/profile ~/.bash_profile ~/.bash_login ~/.profile ~/.bashrc; "
                "do [ -f \"$f\" ] && . \"$f\"; done"
            )

    def _build_locale_setup_snippet(self) -> str:
        """Build bash snippet to set up UTF-8 locale.

        Returns:
            Bash code snippet for locale setup
        """
        return (
            f'export {ENV_VAR_LANG}={DEFAULT_LOCALE}; '
            f'export {ENV_VAR_LC_ALL}={DEFAULT_LOCALE}; '
            f'export {ENV_VAR_LC_CTYPE}={DEFAULT_LOCALE}; '
            f'export {ENV_VAR_PYTHONIOENCODING}=utf-8; '
        )

    def _get_shell_command(self) -> str:
        """Get the appropriate shell command for the platform.

        Returns:
            Shell command name
        """
        return "zsh" if self.platform == "darwin" else "bash"

    def build_agent_launch_command(
        self,
        working_dir: Path,
        agent_command: str
    ) -> str:
        """Build complete bash command to launch agent in working directory.

        Args:
            working_dir: Working directory for the agent
            agent_command: Agent command to run (e.g., "claude")

        Returns:
            Complete bash command string
        """
        path_cleanup = self._build_path_cleanup_snippet()
        profile_source = self._build_profile_source_snippet()
        path_append = self._build_path_append_snippet()
        locale_setup = self._build_locale_setup_snippet()
        shell_cmd = self._get_shell_command()

        cwd_quoted = shlex.quote(str(working_dir))

        command = (
            f'{path_cleanup}'
            f'{profile_source}; '
            f'{path_cleanup}'  # Clean again after profile sourcing
            f'{path_append}'
            f'{locale_setup}'
            f'cd {cwd_quoted} && {agent_command}; '
            f'cd {cwd_quoted}; '
            f'exec {shell_cmd} -i'  # Interactive shell to maintain environment
        )

        return command

    def build_geometry_string(
        self,
        container_width: int,
        container_height: int,
        char_width: int,
        char_height: int,
        padding: int,
        min_cols: int,
        min_rows: int
    ) -> str:
        """Build xterm geometry string.

        Args:
            container_width: Container width in pixels
            container_height: Container height in pixels
            char_width: Character width in pixels
            char_height: Character height in pixels
            padding: Container padding in pixels
            min_cols: Minimum columns
            min_rows: Minimum rows

        Returns:
            Geometry string (e.g., "80x24")
        """
        cols = max(min_cols, (container_width - padding) // char_width)
        rows = max(min_rows, (container_height - padding) // char_height)
        return f"{cols}x{rows}"
