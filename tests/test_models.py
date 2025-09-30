"""Tests for data models."""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QWidget

from models import WorktreeInfo, SessionInfo


class TestWorktreeInfo:
    """Test cases for WorktreeInfo dataclass."""

    def test_worktree_info_creation(self):
        """Test creating a WorktreeInfo instance."""
        path = Path("/test/repo")
        worktree = WorktreeInfo(
            path=path,
            head="abc123",
            branch="refs/heads/main",
            locked=False,
            prunable=False,
            is_main=True
        )
        
        assert worktree.path == path
        assert worktree.head == "abc123"
        assert worktree.branch == "refs/heads/main"
        assert worktree.locked is False
        assert worktree.prunable is False
        assert worktree.is_main is True

    def test_worktree_info_with_none_values(self):
        """Test WorktreeInfo with None values for optional fields."""
        path = Path("/test/detached")
        worktree = WorktreeInfo(
            path=path,
            head=None,
            branch=None,
            locked=True,
            prunable=True,
            is_main=False
        )
        
        assert worktree.path == path
        assert worktree.head is None
        assert worktree.branch is None
        assert worktree.locked is True
        assert worktree.prunable is True
        assert worktree.is_main is False


class TestSessionInfo:
    """Test cases for SessionInfo dataclass."""

    def test_session_info_creation(self):
        """Test creating a SessionInfo instance."""
        path = Path("/test/worktree")
        process = Mock(spec=subprocess.Popen)
        widget = Mock(spec=QWidget)
        start_time = 1234567890.0
        
        session = SessionInfo(
            worktree_path=path,
            process=process,
            container_frame=widget,
            status="running",
            command="bash",
            start_time=start_time
        )
        
        assert session.worktree_path == path
        assert session.process == process
        assert session.container_frame == widget
        assert session.status == "running"
        assert session.command == "bash"
        assert session.start_time == start_time

    def test_session_info_with_none_process(self):
        """Test SessionInfo with None process."""
        path = Path("/test/stopped")
        
        session = SessionInfo(
            worktree_path=path,
            process=None,
            container_frame=None,
            status="stopped",
            command="",
            start_time=0.0
        )
        
        assert session.worktree_path == path
        assert session.process is None
        assert session.container_frame is None
        assert session.status == "stopped"
        assert session.command == ""
        assert session.start_time == 0.0

    def test_session_info_status_values(self):
        """Test different status values for SessionInfo."""
        path = Path("/test/session")
        
        for status in ["running", "stopped", "error"]:
            session = SessionInfo(
                worktree_path=path,
                process=None,
                container_frame=None,
                status=status,
                command="test",
                start_time=0.0
            )
            assert session.status == status
