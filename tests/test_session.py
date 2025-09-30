"""Tests for session management."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from session import SessionManager
from models import SessionInfo


class TestSessionManager:
    """Test SessionManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = SessionManager()
        self.test_path = Path("/test/worktree")
        self.mock_process = Mock()
        self.mock_container = Mock()

    def test_init(self):
        """Test SessionManager initialization."""
        manager = SessionManager()
        assert manager.sessions == {}

    def test_register_session(self):
        """Test registering a new session."""
        command = "bash"
        
        with patch('time.time', return_value=1234567890.0):
            self.session_manager.register_session(
                self.test_path, 
                self.mock_process, 
                self.mock_container, 
                command
            )
        
        path_str = str(self.test_path)
        assert path_str in self.session_manager.sessions
        
        session = self.session_manager.sessions[path_str]
        assert session.worktree_path == self.test_path
        assert session.process == self.mock_process
        assert session.container_frame == self.mock_container
        assert session.status == "running"
        assert session.command == command
        assert session.start_time == 1234567890.0

    def test_register_session_overwrites_existing(self):
        """Test that registering a session overwrites existing one."""
        # Register first session
        self.session_manager.register_session(
            self.test_path, 
            self.mock_process, 
            self.mock_container, 
            "first_command"
        )
        
        # Register second session for same path
        new_process = Mock()
        new_container = Mock()
        
        with patch('time.time', return_value=9999999999.0):
            self.session_manager.register_session(
                self.test_path, 
                new_process, 
                new_container, 
                "second_command"
            )
        
        path_str = str(self.test_path)
        session = self.session_manager.sessions[path_str]
        assert session.process == new_process
        assert session.container_frame == new_container
        assert session.command == "second_command"
        assert session.start_time == 9999999999.0

    def test_get_session_running(self):
        """Test getting a session that is still running."""
        # Register session
        self.session_manager.register_session(
            self.test_path, 
            self.mock_process, 
            self.mock_container, 
            "bash"
        )
        
        # Mock process as still running
        self.mock_process.poll.return_value = None
        
        session = self.session_manager.get_session(self.test_path)
        
        assert session is not None
        assert session.worktree_path == self.test_path
        assert session.process == self.mock_process

    def test_get_session_terminated(self):
        """Test getting a session whose process has terminated."""
        # Register session
        self.session_manager.register_session(
            self.test_path, 
            self.mock_process, 
            self.mock_container, 
            "bash"
        )
        
        # Mock process as terminated
        self.mock_process.poll.return_value = 0
        
        session = self.session_manager.get_session(self.test_path)
        
        assert session is None
        # Session should be removed from manager
        assert str(self.test_path) not in self.session_manager.sessions

    def test_get_session_not_exists(self):
        """Test getting a session that doesn't exist."""
        session = self.session_manager.get_session(self.test_path)
        assert session is None

    def test_get_session_no_process(self):
        """Test getting a session with no process."""
        # Manually create session without process
        path_str = str(self.test_path)
        self.session_manager.sessions[path_str] = SessionInfo(
            worktree_path=self.test_path,
            process=None,
            container_frame=self.mock_container,
            status="stopped",
            command="bash",
            start_time=time.time()
        )
        
        session = self.session_manager.get_session(self.test_path)
        assert session is None

    def test_remove_session_exists(self):
        """Test removing an existing session."""
        # Register session
        self.session_manager.register_session(
            self.test_path, 
            self.mock_process, 
            self.mock_container, 
            "bash"
        )
        
        # Verify session exists
        assert str(self.test_path) in self.session_manager.sessions
        
        # Remove session
        self.session_manager.remove_session(self.test_path)
        
        # Verify session is removed
        assert str(self.test_path) not in self.session_manager.sessions

    def test_remove_session_not_exists(self):
        """Test removing a session that doesn't exist."""
        # Should not raise exception
        self.session_manager.remove_session(self.test_path)
        assert str(self.test_path) not in self.session_manager.sessions

    def test_cleanup_terminated_sessions(self):
        """Test cleanup of terminated sessions."""
        # Register multiple sessions
        path1 = Path("/test/worktree1")
        path2 = Path("/test/worktree2")
        path3 = Path("/test/worktree3")
        
        process1 = Mock()
        process2 = Mock()
        process3 = Mock()
        
        self.session_manager.register_session(path1, process1, Mock(), "bash")
        self.session_manager.register_session(path2, process2, Mock(), "bash")
        self.session_manager.register_session(path3, process3, Mock(), "bash")
        
        # Mock processes: 1 running, 2 terminated
        process1.poll.return_value = None  # Running
        process2.poll.return_value = 0     # Terminated
        process3.poll.return_value = 1     # Terminated with error
        
        self.session_manager.cleanup_terminated_sessions()
        
        # Only running session should remain
        assert str(path1) in self.session_manager.sessions
        assert str(path2) not in self.session_manager.sessions
        assert str(path3) not in self.session_manager.sessions

    def test_cleanup_terminated_sessions_empty(self):
        """Test cleanup when no sessions exist."""
        # Should not raise exception
        self.session_manager.cleanup_terminated_sessions()
        assert self.session_manager.sessions == {}

    def test_cleanup_terminated_sessions_no_process(self):
        """Test cleanup with sessions that have no process."""
        # Create session without process
        path_str = str(self.test_path)
        self.session_manager.sessions[path_str] = SessionInfo(
            worktree_path=self.test_path,
            process=None,
            container_frame=Mock(),
            status="stopped",
            command="bash",
            start_time=time.time()
        )
        
        self.session_manager.cleanup_terminated_sessions()
        
        # Session without process should be removed
        assert path_str not in self.session_manager.sessions

    def test_get_all_sessions(self):
        """Test getting all active sessions."""
        # Register multiple sessions
        path1 = Path("/test/worktree1")
        path2 = Path("/test/worktree2")
        
        process1 = Mock()
        process2 = Mock()
        
        self.session_manager.register_session(path1, process1, Mock(), "bash")
        self.session_manager.register_session(path2, process2, Mock(), "zsh")
        
        # Mock both processes as running
        process1.poll.return_value = None
        process2.poll.return_value = None
        
        sessions = self.session_manager.get_all_sessions()
        
        assert len(sessions) == 2
        session_paths = [s.worktree_path for s in sessions]
        assert path1 in session_paths
        assert path2 in session_paths

    def test_get_all_sessions_filters_terminated(self):
        """Test that get_all_sessions filters out terminated sessions."""
        # Register multiple sessions
        path1 = Path("/test/worktree1")
        path2 = Path("/test/worktree2")
        
        process1 = Mock()
        process2 = Mock()
        
        self.session_manager.register_session(path1, process1, Mock(), "bash")
        self.session_manager.register_session(path2, process2, Mock(), "zsh")
        
        # Mock one running, one terminated
        process1.poll.return_value = None  # Running
        process2.poll.return_value = 0     # Terminated
        
        sessions = self.session_manager.get_all_sessions()
        
        assert len(sessions) == 1
        assert sessions[0].worktree_path == path1

    def test_get_all_sessions_empty(self):
        """Test getting all sessions when none exist."""
        sessions = self.session_manager.get_all_sessions()
        assert sessions == []

    def test_session_count(self):
        """Test getting session count."""
        assert self.session_manager.session_count() == 0
        
        # Add sessions
        self.session_manager.register_session(
            Path("/test/1"), Mock(), Mock(), "bash"
        )
        self.session_manager.register_session(
            Path("/test/2"), Mock(), Mock(), "zsh"
        )
        
        assert self.session_manager.session_count() == 2

    def test_has_session_true(self):
        """Test has_session returns True for existing session."""
        self.session_manager.register_session(
            self.test_path, self.mock_process, self.mock_container, "bash"
        )
        
        # Mock process as running
        self.mock_process.poll.return_value = None
        
        assert self.session_manager.has_session(self.test_path) is True

    def test_has_session_false(self):
        """Test has_session returns False for non-existing session."""
        assert self.session_manager.has_session(self.test_path) is False

    def test_has_session_terminated(self):
        """Test has_session returns False for terminated session."""
        self.session_manager.register_session(
            self.test_path, self.mock_process, self.mock_container, "bash"
        )
        
        # Mock process as terminated
        self.mock_process.poll.return_value = 0
        
        assert self.session_manager.has_session(self.test_path) is False

    def test_terminate_session_success(self):
        """Test terminating a session successfully."""
        self.session_manager.register_session(
            self.test_path, self.mock_process, self.mock_container, "bash"
        )
        
        # Mock process methods
        self.mock_process.poll.return_value = None  # Initially running
        self.mock_process.terminate.return_value = None
        
        result = self.session_manager.terminate_session(self.test_path)
        
        assert result is True
        self.mock_process.terminate.assert_called_once()

    def test_terminate_session_not_exists(self):
        """Test terminating a session that doesn't exist."""
        result = self.session_manager.terminate_session(self.test_path)
        assert result is False

    def test_terminate_session_already_terminated(self):
        """Test terminating a session that's already terminated."""
        self.session_manager.register_session(
            self.test_path, self.mock_process, self.mock_container, "bash"
        )
        
        # Mock process as already terminated
        self.mock_process.poll.return_value = 0
        
        result = self.session_manager.terminate_session(self.test_path)
        
        assert result is False
        self.mock_process.terminate.assert_not_called()

    def test_terminate_all_sessions(self):
        """Test terminating all sessions."""
        # Register multiple sessions
        path1 = Path("/test/worktree1")
        path2 = Path("/test/worktree2")
        
        process1 = Mock()
        process2 = Mock()
        
        self.session_manager.register_session(path1, process1, Mock(), "bash")
        self.session_manager.register_session(path2, process2, Mock(), "zsh")
        
        # Mock processes as running
        process1.poll.return_value = None
        process2.poll.return_value = None
        
        terminated_count = self.session_manager.terminate_all_sessions()
        
        assert terminated_count == 2
        process1.terminate.assert_called_once()
        process2.terminate.assert_called_once()

    def test_terminate_all_sessions_empty(self):
        """Test terminating all sessions when none exist."""
        terminated_count = self.session_manager.terminate_all_sessions()
        assert terminated_count == 0
