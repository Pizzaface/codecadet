"""Tests for configuration management functionality."""

import json
import sys
from pathlib import Path


# Mock PySide6 to avoid GUI dependencies in headless environment
sys.modules['PySide6'] = __import__('unittest.mock').MagicMock()
sys.modules['PySide6.QtWidgets'] = __import__('unittest.mock').MagicMock()
sys.modules['PySide6.QtCore'] = __import__('unittest.mock').MagicMock()

from config import (
    get_agent_command,
    load_config,
    migrate_legacy_config,
    push_recent_branch,
    push_recent_repo,
    remove_agent_config,
    save_config,
    set_agent_config,
    set_default_agent,
)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_existing_file(self, config_file: Path, sample_config: dict):
        """Test loading configuration from existing file."""
        config = load_config(config_file)
        assert config == sample_config

    def test_load_config_nonexistent_file(self, temp_dir: Path):
        """Test loading configuration when file doesn't exist."""
        nonexistent_file = temp_dir / "nonexistent.json"
        config = load_config(nonexistent_file)

        # Should return default config structure
        assert "recent_repos" in config
        assert "recent_branches" in config
        assert "agents" in config
        assert "default_agent" in config
        assert config["recent_repos"] == []
        assert config["recent_branches"] == {}

    def test_load_config_invalid_json(self, temp_dir: Path):
        """Test loading configuration with invalid JSON."""
        invalid_config = temp_dir / "invalid.json"
        invalid_config.write_text("{ invalid json }")

        config = load_config(invalid_config)

        # Should return default config when JSON is invalid
        assert "recent_repos" in config
        assert config["recent_repos"] == []


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_success(self, temp_dir: Path, sample_config: dict):
        """Test saving configuration successfully."""
        config_file = temp_dir / "test_config.json"

        save_config(sample_config, config_file)

        # Verify file was created and contains correct data
        assert config_file.exists()
        saved_data = json.loads(config_file.read_text())
        assert saved_data == sample_config

    def test_save_config_creates_directory(self, temp_dir: Path, sample_config: dict):
        """Test that save_config creates parent directories if needed."""
        nested_path = temp_dir / "nested" / "config.json"

        save_config(sample_config, nested_path)

        assert nested_path.exists()
        saved_data = json.loads(nested_path.read_text())
        assert saved_data == sample_config


class TestRecentRepos:
    """Tests for recent repository management."""

    def test_push_recent_repo_new(self, sample_config: dict):
        """Test adding a new recent repository."""
        repo_path = Path("/test/repo")

        push_recent_repo(sample_config, repo_path)

        assert str(repo_path) in sample_config["recent_repos"]
        assert sample_config["recent_repos"][0] == str(repo_path)

    def test_push_recent_repo_existing(self, sample_config: dict):
        """Test moving existing repository to top of recent list."""
        repo1 = Path("/test/repo1")
        repo2 = Path("/test/repo2")

        # Add two repos
        push_recent_repo(sample_config, repo1)
        push_recent_repo(sample_config, repo2)

        # Add first repo again - should move to top
        push_recent_repo(sample_config, repo1)

        assert sample_config["recent_repos"][0] == str(repo1)
        assert len(sample_config["recent_repos"]) == 2

    def test_push_recent_repo_limit(self, sample_config: dict):
        """Test that recent repos list is limited to 10 items."""
        # Add 12 repositories
        for i in range(12):
            push_recent_repo(sample_config, Path(f"/test/repo{i}"))

        # Should only keep 10 most recent
        assert len(sample_config["recent_repos"]) == 10
        assert sample_config["recent_repos"][0] == "/test/repo11"


class TestRecentBranches:
    """Tests for recent branch management."""

    def test_push_recent_branch_new(self, sample_config: dict):
        """Test adding a new recent branch."""
        repo_path = Path("/test/repo")
        branch = "feature/test"

        push_recent_branch(sample_config, repo_path, branch)

        repo_key = str(repo_path)
        assert repo_key in sample_config["recent_branches"]
        assert branch in sample_config["recent_branches"][repo_key]

    def test_push_recent_branch_existing(self, sample_config: dict):
        """Test moving existing branch to top of recent list."""
        repo_path = Path("/test/repo")
        branch1 = "feature/test1"
        branch2 = "feature/test2"

        push_recent_branch(sample_config, repo_path, branch1)
        push_recent_branch(sample_config, repo_path, branch2)
        push_recent_branch(sample_config, repo_path, branch1)

        repo_key = str(repo_path)
        branches = sample_config["recent_branches"][repo_key]
        assert branches[0] == branch1
        assert len(branches) == 2


class TestAgentManagement:
    """Tests for agent configuration management."""

    def test_get_agent_command_existing(self, sample_config: dict):
        """Test getting command for existing agent."""
        command = get_agent_command(sample_config, "default")
        assert command == ["claude"]

    def test_get_agent_command_nonexistent(self, sample_config: dict):
        """Test getting command for non-existent agent."""
        command = get_agent_command(sample_config, "nonexistent")
        assert command == ["claude"]  # Should return default

    def test_get_agent_command_none(self, sample_config: dict):
        """Test getting command when agent_id is None."""
        command = get_agent_command(sample_config, None)
        assert command == ["claude"]  # Should return default agent

    def test_set_agent_config(self, sample_config: dict):
        """Test setting agent configuration."""
        set_agent_config(sample_config, "test_agent", "test-command", ["--arg1", "--arg2"])

        assert "test_agent" in sample_config["agents"]
        agent_config = sample_config["agents"]["test_agent"]
        assert agent_config["command"] == "test-command"
        assert agent_config["args"] == ["--arg1", "--arg2"]

    def test_remove_agent_config(self, sample_config: dict):
        """Test removing agent configuration."""
        # Add an agent first
        set_agent_config(sample_config, "test_agent", "test-command", [])
        assert "test_agent" in sample_config["agents"]

        # Remove it
        remove_agent_config(sample_config, "test_agent")
        assert "test_agent" not in sample_config["agents"]

    def test_set_default_agent(self, sample_config: dict):
        """Test setting default agent."""
        set_agent_config(sample_config, "new_agent", "new-command", [])
        set_default_agent(sample_config, "new_agent")

        assert sample_config["default_agent"] == "new_agent"


class TestMigrateLegacyConfig:
    """Tests for legacy configuration migration."""

    def test_migrate_legacy_config_needed(self):
        """Test migration when legacy config structure is detected."""
        legacy_config = {
            "claude_command": "claude-legacy",
            "claude_args": ["--legacy"],
            "recent_repos": ["/old/repo"]
        }

        migrate_legacy_config(legacy_config)

        # Should have new structure
        assert "agents" in legacy_config
        assert "default_agent" in legacy_config
        assert legacy_config["agents"]["default"]["command"] == "claude-legacy"
        assert legacy_config["agents"]["default"]["args"] == ["--legacy"]

        # Old keys should be removed
        assert "claude_command" not in legacy_config
        assert "claude_args" not in legacy_config

    def test_migrate_legacy_config_not_needed(self, sample_config: dict):
        """Test migration when config is already in new format."""
        original_config = sample_config.copy()

        migrate_legacy_config(sample_config)

        # Should remain unchanged
        assert sample_config == original_config

