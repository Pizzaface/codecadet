"""Session management for terminal sessions in worktrees."""

import logging
import time
from pathlib import Path

from models import SessionInfo


class SessionManager:
    """Tracks terminal sessions for each worktree path."""

    def __init__(self):
        self.sessions: dict[str, SessionInfo] = {}  # {worktree_path_str: SessionInfo}

    def register_session(self, worktree_path: Path, process: Any,
                         container_frame: Any, command: str) -> None:
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
            # Terminate process if still running
            if session.process and session.process.poll() is None:
                try:
                    session.process.terminate()
                except (ProcessLookupError, OSError) as e:
                    logging.warning(f"Failed to terminate process for {path_str}: {e}")
                    pass
            # Destroy the container frame if it exists
            if session.container_frame:
                try:
                    session.container_frame.destroy()
                except (AttributeError, RuntimeError) as e:
                    logging.warning(f"Failed to destroy container frame for {path_str}: {e}")
                    pass
            del self.sessions[path_str]

    def get_all_sessions(self) -> dict[str, SessionInfo]:
        """Get all sessions (active and inactive)."""
        return self.sessions.copy()

    def cleanup_terminated_sessions(self) -> None:
        """Clean up sessions with terminated processes."""
        to_remove = []
        for path_str, session in self.sessions.items():
            if session.process and session.process.poll() is not None:
                to_remove.append(Path(path_str))

        for path in to_remove:
            self.remove_session(path)





