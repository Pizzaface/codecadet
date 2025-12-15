"""Session management for terminal sessions in worktrees."""

import time
from pathlib import Path
from typing import Dict, Optional
import uuid

from models import SessionInfo


class SessionManager:
    """Tracks terminal sessions for each worktree path with multi-tab support."""

    def __init__(self, max_tabs_per_worktree: int = 10):
        self.sessions: Dict[str, Dict[str, SessionInfo]] = {}  # {worktree_path_str: {tab_id: SessionInfo}}
        self.max_tabs_per_worktree = max_tabs_per_worktree

    def _generate_tab_name(self, worktree_path: Path, base_name: str) -> str:
        """Generate a unique tab name based on agent name, incrementing if duplicates exist."""
        path_str = str(worktree_path)
        worktree_sessions = self.sessions.get(path_str, {})

        # Count existing tabs with the same base name
        existing_names = [s.tab_name for s in worktree_sessions.values()]

        # Check if base name (without number) already exists
        count = 0
        for name in existing_names:
            if name == base_name:
                count += 1
            elif name.startswith(base_name + " (") and name.endswith(")"):
                # Extract number from "Agent Name (N)"
                try:
                    num = int(name[len(base_name) + 2:-1])
                    count = max(count, num)
                except ValueError:
                    pass

        if count == 0 and base_name not in existing_names:
            return base_name
        else:
            return f"{base_name} ({count + 1})"

    def register_session(self, worktree_path: Path, process,
                         container_frame, command: str, tab_name: Optional[str] = None,
                         agent_name: Optional[str] = None) -> str:
        """Register a new terminal session for a worktree and return the tab_id."""
        path_str = str(worktree_path)

        # Initialize worktree sessions dict if needed
        if path_str not in self.sessions:
            self.sessions[path_str] = {}

        # Check tab limit
        if len(self.sessions[path_str]) >= self.max_tabs_per_worktree:
            raise ValueError(f"Maximum {self.max_tabs_per_worktree} tabs per worktree reached")

        # Generate unique tab ID and name
        tab_id = str(uuid.uuid4())[:8]  # Short UUID4
        if not tab_name:
            # Use agent name as base, default to "Terminal" if not provided
            base_name = agent_name if agent_name else "Terminal"
            tab_name = self._generate_tab_name(worktree_path, base_name)
        
        self.sessions[path_str][tab_id] = SessionInfo(
            worktree_path=worktree_path,
            process=process,
            container_frame=container_frame,
            status="running",
            command=command,
            start_time=time.time(),
            tab_id=tab_id,
            tab_name=tab_name
        )
        
        return tab_id

    def get_session(self, worktree_path: Path, tab_id: str) -> SessionInfo | None:
        """Get session info for a specific worktree tab if it exists and is active."""
        path_str = str(worktree_path)
        worktree_sessions = self.sessions.get(path_str, {})
        session = worktree_sessions.get(tab_id)

        if session and session.process:
            # Check if process is still running
            if session.process.poll() is None:
                return session
            else:
                # Process terminated, clean up
                self.remove_session(worktree_path, tab_id)

        return None
    
    def get_active_session(self, worktree_path: Path) -> SessionInfo | None:
        """Get the first active session for a worktree (for backward compatibility)."""
        path_str = str(worktree_path)
        worktree_sessions = self.sessions.get(path_str, {})
        
        for tab_id, session in worktree_sessions.items():
            active_session = self.get_session(worktree_path, tab_id)
            if active_session:
                return active_session
        
        return None
    
    def get_all_sessions_for_worktree(self, worktree_path: Path) -> Dict[str, SessionInfo]:
        """Get all sessions (active and inactive) for a worktree."""
        path_str = str(worktree_path)
        return self.sessions.get(path_str, {}).copy()

    def remove_session(self, worktree_path: Path, tab_id: str):
        """Remove a specific session for a worktree."""
        path_str = str(worktree_path)
        worktree_sessions = self.sessions.get(path_str, {})
        
        if tab_id in worktree_sessions:
            session = worktree_sessions[tab_id]
            # Terminate process if still running
            if session.process and session.process.poll() is None:
                try:
                    session.process.terminate()
                except Exception:
                    pass
            # Destroy the container frame if it exists
            if session.container_frame:
                try:
                    session.container_frame.deleteLater()
                except Exception:
                    pass
            del worktree_sessions[tab_id]
            
            # Clean up empty worktree dict
            if not worktree_sessions:
                del self.sessions[path_str]
    
    def remove_all_sessions_for_worktree(self, worktree_path: Path):
        """Remove all sessions for a worktree."""
        path_str = str(worktree_path)
        if path_str in self.sessions:
            # Copy tab_ids to avoid modifying dict during iteration
            tab_ids = list(self.sessions[path_str].keys())
            for tab_id in tab_ids:
                self.remove_session(worktree_path, tab_id)

    def get_all_sessions(self) -> Dict[str, Dict[str, SessionInfo]]:
        """Get all sessions (active and inactive) for all worktrees."""
        return {path: sessions.copy() for path, sessions in self.sessions.items()}
    
    def rename_tab(self, worktree_path: Path, tab_id: str, new_name: str):
        """Rename a tab."""
        path_str = str(worktree_path)
        worktree_sessions = self.sessions.get(path_str, {})
        
        if tab_id in worktree_sessions:
            session = worktree_sessions[tab_id]
            session.tab_name = new_name

    def cleanup_terminated_sessions(self):
        """Clean up sessions with terminated processes across all worktrees."""
        to_remove = []
        for path_str, worktree_sessions in self.sessions.items():
            for tab_id, session in worktree_sessions.items():
                if session.process and session.process.poll() is not None:
                    to_remove.append((Path(path_str), tab_id))

        for worktree_path, tab_id in to_remove:
            self.remove_session(worktree_path, tab_id)
