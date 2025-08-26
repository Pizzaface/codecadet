"""Data models for Git Worktree Manager."""

import subprocess
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path


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
    container_frame: tk.Frame | None  # The frame containing the xterm
    status: str  # "running", "stopped", "error"
    command: str
    start_time: float
