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
    "claude_command": "claude",  # override if you use a different CLI (deprecated, use coding_agents)
    "recent_branches": {},  # dict[str, list[str]] - repo_path -> [branch_names]
    "coding_agents": {  # dict[str, dict] - agent configurations
        "claude": {
            "command": "claude",
            "name": "Claude Code",
            "enabled": True
        }
    },
    "default_agent": "claude",  # str - default agent to use
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
        # Migrate legacy configuration
        migrate_legacy_config(cfg)
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


def get_coding_agents(cfg: dict) -> dict:
    """Get all coding agent configurations."""
    return cfg.get("coding_agents", {})


def get_agent_config(cfg: dict, agent_id: str) -> dict | None:
    """Get configuration for a specific agent."""
    agents = get_coding_agents(cfg)
    return agents.get(agent_id)


def get_default_agent(cfg: dict) -> str:
    """Get the default agent ID."""
    return cfg.get("default_agent", "claude")


def set_agent_config(cfg: dict, agent_id: str, name: str, command: str, enabled: bool = True):
    """Set configuration for a coding agent."""
    agents = cfg.setdefault("coding_agents", {})
    agents[agent_id] = {
        "name": name,
        "command": command,
        "enabled": enabled
    }


def remove_agent_config(cfg: dict, agent_id: str):
    """Remove a coding agent configuration."""
    agents = cfg.get("coding_agents", {})
    if agent_id in agents:
        del agents[agent_id]
        # If removing the default agent, set a new default
        if cfg.get("default_agent") == agent_id:
            remaining_agents = [aid for aid, aconf in agents.items() if aconf.get("enabled", True)]
            cfg["default_agent"] = remaining_agents[0] if remaining_agents else "claude"


def set_default_agent(cfg: dict, agent_id: str):
    """Set the default coding agent."""
    agents = get_coding_agents(cfg)
    if agent_id in agents and agents[agent_id].get("enabled", True):
        cfg["default_agent"] = agent_id


def get_agent_command(cfg: dict, agent_id: str = None) -> str:
    """Get the command for a specific agent, or the default agent."""
    if agent_id is None:
        agent_id = get_default_agent(cfg)
    
    agent_config = get_agent_config(cfg, agent_id)
    if agent_config:
        return agent_config.get("command", "claude")
    
    # Fallback to legacy claude_command for backwards compatibility
    if agent_id == "claude":
        return cfg.get("claude_command", "claude")
    
    return "claude"


def migrate_legacy_config(cfg: dict):
    """Migrate legacy claude_command to new coding_agents structure."""
    if "claude_command" in cfg and "coding_agents" not in cfg:
        claude_cmd = cfg["claude_command"]
        cfg["coding_agents"] = {
            "claude": {
                "command": claude_cmd,
                "name": "Claude Code",
                "enabled": True
            }
        }
        cfg["default_agent"] = "claude"
