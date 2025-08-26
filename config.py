"""Configuration management for Git Worktree Manager."""

import os
import sys
import json
from pathlib import Path

APP_NAME = "WorktreeManagerClaude"
RECENTS_MAX = 15
RECENT_BRANCHES_MAX = 10

DEFAULT_CONFIG = {
    "recent_repos": [],  # list[str]
    "last_repo": None,  # str | None
    "auto_reopen_last": True,  # bool
    "window_geometry": None,  # str | None
    "theme": "dark",  # "dark" | "light"
    "embed_terminal": True,  # try to embed xterm on Linux
    "claude_command": "claude",  # override if you use a different CLI
    "recent_branches": {},  # dict[str, list[str]] - repo_path -> [branch_names]
}


def _config_dir() -> Path:
    """Get the platform-specific configuration directory."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        return Path(base) / APP_NAME


def _config_path() -> Path:
    """Get the configuration file path."""
    return _config_dir() / "settings.json"


def load_config() -> dict:
    """Load configuration from file, falling back to defaults."""
    p = _config_path()
    try:
        with p.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        # Fill any missing keys with defaults
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    """Save configuration to file."""
    d = _config_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / ".settings.tmp"
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    tmp.replace(_config_path())


def push_recent_repo(cfg: dict, repo_root: Path):
    """Add a repository to the recent repositories list."""
    s = str(repo_root)
    recents = [r for r in cfg.get("recent_repos", []) if r != s]
    recents.insert(0, s)
    if len(recents) > RECENTS_MAX:
        recents = recents[:RECENTS_MAX]
    cfg["recent_repos"] = recents
    cfg["last_repo"] = s


def push_recent_branch(cfg: dict, repo_root: Path, branch: str):
    """Add a branch to the recent branches list for a specific repository."""
    repo_key = str(repo_root)
    recent_branches = cfg.setdefault("recent_branches", {})
    branch_list = recent_branches.setdefault(repo_key, [])
    
    # Remove if already exists to avoid duplicates
    if branch in branch_list:
        branch_list.remove(branch)
    
    # Insert at beginning
    branch_list.insert(0, branch)
    
    # Limit the list size
    if len(branch_list) > RECENT_BRANCHES_MAX:
        branch_list = branch_list[:RECENT_BRANCHES_MAX]
    
    recent_branches[repo_key] = branch_list


def get_recent_branches(cfg: dict, repo_root: Path) -> list[str]:
    """Get recent branches for a specific repository."""
    repo_key = str(repo_root)
    return cfg.get("recent_branches", {}).get(repo_key, [])
