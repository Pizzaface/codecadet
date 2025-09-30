"""Session management for terminal sessions in worktrees."""

import time
from pathlib import Path
from typing import Dict

from models import SessionInfo
from logging_config import get_logger
from metrics import record_error

logger = get_logger(__name__)


class SessionManager:
    """Tracks terminal sessions for each worktree path."""

    def __init__(self):
        self.sessions: Dict[str, SessionInfo] = {}  # {worktree_path_str: SessionInfo}

    def register_session(self, worktree_path: Path, process, 
                         container_frame, command: str):
        """Register a new terminal session for a worktree."""
        path_str = str(worktree_path)
        self.sessions[path_str] = SessionInfo(
            worktree_path=worktree_path,
            process=process,
            container_frame=container_frame,
            status="running",
            command=command,
            start_time=time.time()
        )
        logger.info(f"Registered terminal session for worktree {worktree_path} with command: {command}")

    def get_session(self, worktree_path: Path) -> SessionInfo | None:
        """Get session info for a worktree if it exists and is active."""
        path_str = str(worktree_path)
        session = self.sessions.get(path_str)

        if session and session.process:
            # Check if process is still running
            if session.process.poll() is None:
                return session
            else:
                # Process terminated, clean up
                self.remove_session(worktree_path)

        return None

    def remove_session(self, worktree_path: Path):
        """Remove a session for a worktree."""
        path_str = str(worktree_path)
        if path_str in self.sessions:
            session = self.sessions[path_str]
            
            # Calculate session duration and record metrics
            if hasattr(session, 'start_time') and session.start_time:
                duration_seconds = time.time() - session.start_time
                try:
                    from metrics import get_metrics_collector
                    collector = get_metrics_collector()
                    if collector:
                        # Estimate command count (simplified)
                        command_count = 1  # Basic estimate, could be enhanced
                        collector.record_terminal_session(duration_seconds, command_count)
                        logger.debug(f"Recorded terminal session metrics: {duration_seconds:.1f}s")
                except Exception as e:
                    logger.debug(f"Failed to record session metrics: {e}")
            
            # Terminate process if still running
            if session.process and session.process.poll() is None:
                try:
                    session.process.terminate()
                    logger.debug(f"Terminated process for session {worktree_path}")
                except Exception as e:
                    logger.warning(f"Failed to terminate process for session {worktree_path}: {e}")
                    record_error("session_termination_failed", str(e), {"worktree_path": str(worktree_path)})
            
            # Destroy the container frame if it exists
            if session.container_frame:
                try:
                    session.container_frame.destroy()
                    logger.debug(f"Destroyed container frame for session {worktree_path}")
                except Exception as e:
                    logger.warning(f"Failed to destroy container frame for session {worktree_path}: {e}")
                    record_error("container_frame_destroy_failed", str(e), {"worktree_path": str(worktree_path)})
            
            del self.sessions[path_str]

    def get_all_sessions(self) -> Dict[str, SessionInfo]:
        """Get all sessions (active and inactive)."""
        return self.sessions.copy()

    def cleanup_terminated_sessions(self):
        """Clean up sessions with terminated processes."""
        to_remove = []
        for path_str, session in self.sessions.items():
            if session.process and session.process.poll() is not None:
                to_remove.append(Path(path_str))

        for path in to_remove:
            self.remove_session(path)





