"""Data models for Git Worktree Manager."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QWidget


@dataclass
class WorktreeInfo:
    """Information about a Git worktree."""
    path: Path
    head: str | None
    branch: str | None  # 'refs/heads/feature-x' or None (detached)
    locked: bool
    prunable: bool
    is_main: bool


@dataclass
class SessionInfo:
    """Information about a terminal session for a worktree."""
    worktree_path: Path
    process: subprocess.Popen | None
    container_frame: QWidget | None  # The frame containing the xterm
    status: str  # "running", "stopped", "error"
    command: str
    start_time: float
    tab_id: str  # Unique identifier for the tab within the worktree
    tab_name: str  # Display name for the tab
