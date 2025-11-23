"""Shared utility functions and classes.

This module contains common utilities used across the application,
following the DRY principle.
"""

import os
from pathlib import Path
from typing import Protocol, Optional


class TerminalProcess(Protocol):
    """Protocol for terminal process objects.

    This defines the interface that terminal process wrappers must implement,
    allowing for different implementations (subprocess, PTY, web terminal, etc.)
    """

    def poll(self) -> Optional[int]:
        """Check if process is still running.

        Returns:
            None if running, exit code if terminated
        """
        ...

    def terminate(self) -> None:
        """Terminate the process."""
        ...


class MockTerminalProcess:
    """Mock process wrapper for PTY and web terminal widgets.

    This class provides a uniform interface for session management,
    wrapping terminal widgets to look like subprocess.Popen objects.
    """

    def __init__(self, widget):
        """Initialize mock process with a terminal widget.

        Args:
            widget: Terminal widget (PTYTerminalWidget or WebTerminalWidget)
        """
        self.widget = widget

    def poll(self) -> Optional[int]:
        """Check if the terminal process is still running.

        Returns:
            None if running, 0 if terminated
        """
        # For web terminal
        if hasattr(self.widget, 'bridge') and hasattr(self.widget.bridge, 'process_pid'):
            try:
                os.kill(self.widget.bridge.process_pid, 0)
                return None  # Still running
            except OSError:
                return 0  # Process ended

        # For PTY terminal
        if hasattr(self.widget, 'process_pid'):
            try:
                os.kill(self.widget.process_pid, 0)
                return None  # Still running
            except OSError:
                return 0  # Process ended

        return 0

    def terminate(self) -> None:
        """Terminate the terminal widget."""
        if hasattr(self.widget, 'cleanup'):
            self.widget.cleanup()
        elif hasattr(self.widget, '_cleanup'):
            self.widget._cleanup()


def remove_path_entry(path_value: str, entry: str) -> str:
    """Remove all occurrences of an entry from a PATH-like string.

    Args:
        path_value: PATH environment variable value
        entry: Entry to remove

    Returns:
        Cleaned PATH string

    Example:
        >>> remove_path_entry("/usr/bin:/tmp:/usr/local/bin", "/tmp")
        '/usr/bin:/usr/local/bin'
    """
    if not path_value or not entry:
        return path_value

    sep = os.pathsep
    parts = path_value.split(sep)
    cleaned = [part for part in parts if part != entry]
    return sep.join(cleaned)


def truncate_path_for_display(path: Path, max_length: int = 50) -> str:
    """Truncate a path for display in the UI.

    Args:
        path: Path to truncate
        max_length: Maximum display length

    Returns:
        Truncated path string with ellipsis if needed

    Example:
        >>> truncate_path_for_display(Path("/very/long/path/to/file.txt"), 20)
        '...to/file.txt'
    """
    path_str = str(path)
    if len(path_str) <= max_length:
        return path_str

    prefix_len = len("...")
    return "..." + path_str[-(max_length - prefix_len):]


def clean_branch_name(branch: str) -> str:
    """Clean Git branch name by removing common prefixes.

    Args:
        branch: Git branch reference

    Returns:
        Cleaned branch name

    Example:
        >>> clean_branch_name("refs/heads/feature/new-feature")
        'feature/new-feature'
        >>> clean_branch_name("remotes/origin/main")
        'main'
    """
    if not branch:
        return branch

    # Remove refs/heads/ prefix
    if branch.startswith("refs/heads/"):
        branch = branch[11:]

    # Remove remotes/origin/ prefix
    if branch.startswith("remotes/origin/"):
        branch = branch[15:]

    return branch


def format_geometry_string(width: int, height: int, x: int, y: int) -> str:
    """Format window geometry as a string.

    Args:
        width: Window width
        height: Window height
        x: X position
        y: Y position

    Returns:
        Geometry string in format "WIDTHxHEIGHT+X+Y"

    Example:
        >>> format_geometry_string(1000, 600, 100, 100)
        '1000x600+100+100'
    """
    return f"{width}x{height}+{x}+{y}"


def parse_geometry_string(geometry: str) -> Optional[tuple[int, int, int, int]]:
    """Parse a geometry string to extract dimensions and position.

    Args:
        geometry: Geometry string in format "WIDTHxHEIGHT+X+Y"

    Returns:
        Tuple of (width, height, x, y) or None if parsing fails

    Example:
        >>> parse_geometry_string("1000x600+100+100")
        (1000, 600, 100, 100)
    """
    try:
        if 'x' in geometry and '+' in geometry:
            size_part, pos_part = geometry.split('+', 1)
            width, height = map(int, size_part.split('x'))
            x, y = map(int, pos_part.split('+'))
            return width, height, x, y
    except (ValueError, AttributeError):
        pass
    return None
