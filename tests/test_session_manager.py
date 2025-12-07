import time
from pathlib import Path

import pytest

import session
from models import SessionInfo


class DummyProcess:
    """Simple dummy process object with configurable poll result."""

    def __init__(self, alive: bool = True):
        self._alive = alive

    def poll(self):  # Mimic subprocess API
        return None if self._alive else 0

    def terminate(self):  # Called by SessionManager.remove_session
        self._alive = False


def make_manager(max_tabs: int = 3) -> session.SessionManager:
    return session.SessionManager(max_tabs_per_worktree=max_tabs)


def test_register_and_get_session_basic():
    manager = make_manager()
    worktree = Path("/tmp/worktree-basic")
    proc = DummyProcess(alive=True)

    tab_id = manager.register_session(worktree, proc, container_frame=None, command="claude")

    # Session is stored under the worktree path with a short UUID tab_id
    all_sessions = manager.get_all_sessions_for_worktree(worktree)
    assert tab_id in all_sessions

    info = manager.get_session(worktree, tab_id)
    assert isinstance(info, SessionInfo)
    assert info.worktree_path == worktree
    assert info.process is proc
    assert info.command == "claude"
    assert info.tab_id == tab_id
    assert info.tab_name.startswith("Terminal ")


def test_max_tabs_enforced():
    manager = make_manager(max_tabs=2)
    worktree = Path("/tmp/worktree-max-tabs")

    manager.register_session(worktree, DummyProcess(), None, "cmd1")
    manager.register_session(worktree, DummyProcess(), None, "cmd2")

    with pytest.raises(ValueError) as exc:
        manager.register_session(worktree, DummyProcess(), None, "cmd3")

    assert str(manager.max_tabs_per_worktree) in str(exc.value)


def test_get_session_cleans_up_terminated_process():
    manager = make_manager()
    worktree = Path("/tmp/worktree-cleanup")
    proc = DummyProcess(alive=True)
    tab_id = manager.register_session(worktree, proc, None, "cmd")

    # Initially, session is returned
    assert manager.get_session(worktree, tab_id) is not None

    # Mark process as terminated; next get_session should clean it up
    proc._alive = False
    assert manager.get_session(worktree, tab_id) is None

    # Session should be removed from the internal mapping
    assert tab_id not in manager.get_all_sessions_for_worktree(worktree)


def test_cleanup_terminated_sessions_removes_only_dead_processes():
    manager = make_manager()
    wt1 = Path("/tmp/wt1")
    wt2 = Path("/tmp/wt2")

    alive_proc = DummyProcess(alive=True)
    dead_proc = DummyProcess(alive=False)

    tab_alive = manager.register_session(wt1, alive_proc, None, "alive")
    tab_dead = manager.register_session(wt1, dead_proc, None, "dead")
    tab_other = manager.register_session(wt2, DummyProcess(alive=False), None, "other")

    manager.cleanup_terminated_sessions()

    wt1_sessions = manager.get_all_sessions_for_worktree(wt1)
    wt2_sessions = manager.get_all_sessions_for_worktree(wt2)

    # Alive process remains
    assert tab_alive in wt1_sessions
    # Dead ones are removed
    assert tab_dead not in wt1_sessions
    assert tab_other not in wt2_sessions
