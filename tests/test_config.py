"""Tests for configuration management."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from config import (
    APP_NAME, RECENTS_MAX, RECENT_BRANCHES_MAX, DEFAULT_CONFIG,
    _config_dir, _config_path, load_config, save_config,
    migrate_legacy_config, push_recent_repo, push_recent_branch, get_recent_branches
)


class TestConstants:
    """Test configuration constants."""

    def test_app_name(self):
        """Test APP_NAME constant."""
        assert APP_NAME == "WorktreeManagerClaude"

    def test_recents_max(self):
        """Test RECENTS_MAX constant."""
        assert RECENTS_MAX == 15

    def test_recent_branches_max(self):
        """Test RECENT_BRANCHES_MAX constant."""
        assert RECENT_BRANCHES_MAX == 10

    def test_default_config_structure(self):
        """Test DEFAULT_CONFIG has expected structure."""
        expected_keys = {
            "recent_repos", "last_repo", "auto_reopen_last",
            "window_geometry", "theme", "embed_terminal",
            "claude_command", "recent_branches", "coding_agents",
            "default_agent"
        }
        assert set(DEFAULT_CONFIG.keys()) == expected_keys

    def test_default_config_values(self):
        """Test DEFAULT_CONFIG has expected default values."""
        assert DEFAULT_CONFIG["recent_repos"] == []
        assert DEFAULT_CONFIG["last_repo"] is None
        assert DEFAULT_CONFIG["auto_reopen_last"] is True
        assert DEFAULT_CONFIG["window_geometry"] is None
        assert DEFAULT_CONFIG["theme"] == "dark"
        assert DEFAULT_CONFIG["embed_terminal"] is True
        assert DEFAULT_CONFIG["claude_command"] == "claude"
        assert DEFAULT_CONFIG["recent_branches"] == {}
        assert isinstance(DEFAULT_CONFIG["coding_agents"], dict)
        assert DEFAULT_CONFIG["default_agent"] == "claude"


class TestConfigDir:
    """Test configuration directory functions."""

    @patch.dict(os.environ, {"APPDATA": "/test/appdata"})
    @patch("sys.platform", "win32")
    def test_config_dir_windows_with_appdata(self):
        """Test config directory on Windows with APPDATA."""
        result = _config_dir()
        expected = Path("/test/appdata") / APP_NAME
        assert result == expected

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.platform", "win32")
    @patch("pathlib.Path.home")
    def test_config_dir_windows_without_appdata(self, mock_home):
        """Test config directory on Windows without APPDATA."""
        mock_home.return_value = Path("/test/home")
        result = _config_dir()
        expected = Path("/test/home/AppData/Roaming") / APP_NAME
        assert result == expected

    @patch("sys.platform", "darwin")
    @patch("pathlib.Path.home")
    def test_config_dir_macos(self, mock_home):
        """Test config directory on macOS."""
        mock_home.return_value = Path("/test/home")
        result = _config_dir()
        expected = Path("/test/home/Library/Application Support") / APP_NAME
        assert result == expected

    @patch.dict(os.environ, {"XDG_CONFIG_HOME": "/test/xdg"})
    @patch("sys.platform", "linux")
    def test_config_dir_linux_with_xdg(self):
        """Test config directory on Linux with XDG_CONFIG_HOME."""
        result = _config_dir()
        expected = Path("/test/xdg") / APP_NAME
        assert result == expected

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.platform", "linux")
    @patch("pathlib.Path.home")
    def test_config_dir_linux_without_xdg(self, mock_home):
        """Test config directory on Linux without XDG_CONFIG_HOME."""
        mock_home.return_value = Path("/test/home")
        result = _config_dir()
        expected = Path("/test/home/.config") / APP_NAME
        assert result == expected

    @patch("config._config_dir")
    def test_config_path(self, mock_config_dir):
        """Test config file path."""
        mock_config_dir.return_value = Path("/test/config")
        result = _config_path()
        expected = Path("/test/config/settings.json")
        assert result == expected


class TestLoadConfig:
    """Test load_config function."""

    @patch("config._config_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_success(self, mock_file, mock_config_path):
        """Test loading configuration successfully."""
        mock_config_path.return_value = Path("/test/settings.json")
        test_config = {"theme": "light", "recent_repos": ["/test/repo"]}
        mock_file.return_value.read.return_value = json.dumps(test_config)

        result = load_config()

        # Should merge with defaults
        expected = DEFAULT_CONFIG.copy()
        expected.update(test_config)
        assert result == expected

    @patch("config._config_path")
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_config_file_not_found(self, mock_file, mock_config_path):
        """Test loading configuration when file doesn't exist."""
        mock_config_path.return_value = Path("/test/settings.json")

        result = load_config()

        assert result == DEFAULT_CONFIG.copy()

    @patch("config._config_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_invalid_json(self, mock_file, mock_config_path):
        """Test loading configuration with invalid JSON."""
        mock_config_path.return_value = Path("/test/settings.json")
        mock_file.return_value.read.return_value = "invalid json"

        result = load_config()

        assert result == DEFAULT_CONFIG.copy()

    @patch("config._config_path")
    @patch("builtins.open", side_effect=PermissionError)
    def test_load_config_permission_error(self, mock_file, mock_config_path):
        """Test loading configuration with permission error."""
        mock_config_path.return_value = Path("/test/settings.json")

        result = load_config()

        assert result == DEFAULT_CONFIG.copy()

    @patch("config.migrate_legacy_config")
    @patch("config._config_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_calls_migration(self, mock_file, mock_config_path, mock_migrate):
        """Test that load_config calls migration."""
        mock_config_path.return_value = Path("/test/settings.json")
        test_config = {"theme": "light"}
        mock_file.return_value.read.return_value = json.dumps(test_config)

        load_config()

        mock_migrate.assert_called_once()


class TestSaveConfig:
    """Test save_config function."""

    @patch("config._config_path")
    @patch("config._config_dir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.replace")
    def test_save_config_success(self, mock_replace, mock_mkdir, mock_file, mock_config_dir, mock_config_path):
        """Test saving configuration successfully."""
        mock_config_dir.return_value = Path("/test/config")
        mock_config_path.return_value = Path("/test/config/settings.json")
        test_config = {"theme": "light", "recent_repos": []}

        save_config(test_config)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called()
        mock_replace.assert_called_once()

    @patch("config._config_path")
    @patch("config._config_dir")
    @patch("builtins.open", side_effect=PermissionError)
    @patch("pathlib.Path.mkdir")
    def test_save_config_permission_error(self, mock_mkdir, mock_file, mock_config_dir, mock_config_path):
        """Test saving configuration with permission error."""
        mock_config_dir.return_value = Path("/test/config")
        mock_config_path.return_value = Path("/test/config/settings.json")
        test_config = {"theme": "light"}

        # Should not raise exception
        save_config(test_config)

    @patch("config._config_path")
    @patch("config._config_dir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir", side_effect=OSError)
    def test_save_config_mkdir_error(self, mock_mkdir, mock_file, mock_config_dir, mock_config_path):
        """Test saving configuration when mkdir fails."""
        mock_config_dir.return_value = Path("/test/config")
        mock_config_path.return_value = Path("/test/config/settings.json")
        test_config = {"theme": "light"}

        # Should not raise exception
        save_config(test_config)


class TestMigrateLegacyConfig:
    """Test migrate_legacy_config function."""

    def test_migrate_legacy_config_no_changes(self):
        """Test migration when no changes needed."""
        config = {"theme": "dark", "recent_repos": []}
        original = config.copy()
        
        migrate_legacy_config(config)
        
        assert config == original

    def test_migrate_legacy_config_with_changes(self):
        """Test migration with legacy settings."""
        config = {
            "theme": "dark",
            "recent_repos": [],
            "old_setting": "value"  # This would be a legacy setting
        }
        
        migrate_legacy_config(config)
        
        # Function should handle legacy settings gracefully
        assert "theme" in config
        assert "recent_repos" in config


class TestRecentRepos:
    """Test recent repositories management."""

    def test_push_recent_repo_new(self):
        """Test adding a new recent repository."""
        config = {"recent_repos": []}
        repo_path = Path("/test/repo")
        
        push_recent_repo(config, repo_path)
        
        assert config["recent_repos"] == ["/test/repo"]
        assert config["last_repo"] == "/test/repo"

    def test_push_recent_repo_existing(self):
        """Test adding an existing repository moves it to front."""
        config = {"recent_repos": ["/test/repo1", "/test/repo2", "/test/repo3"]}
        repo_path = Path("/test/repo2")
        
        push_recent_repo(config, repo_path)
        
        assert config["recent_repos"] == ["/test/repo2", "/test/repo1", "/test/repo3"]
        assert config["last_repo"] == "/test/repo2"

    def test_push_recent_repo_max_limit(self):
        """Test adding repository respects maximum limit."""
        # Create list at maximum capacity
        repos = [f"/test/repo{i}" for i in range(RECENTS_MAX)]
        config = {"recent_repos": repos}
        new_repo = Path("/test/new_repo")
        
        push_recent_repo(config, new_repo)
        
        assert len(config["recent_repos"]) == RECENTS_MAX
        assert config["recent_repos"][0] == "/test/new_repo"
        assert f"/test/repo{RECENTS_MAX-1}" not in config["recent_repos"]

    def test_get_recent_repos(self):
        """Test getting recent repositories."""
        repos = ["/test/repo1", "/test/repo2"]
        config = {"recent_repos": repos}
        
        result = config.get("recent_repos", [])
        
        assert result == repos

    def test_get_recent_repos_empty(self):
        """Test getting recent repositories when none exist."""
        config = {"recent_repos": []}
        
        result = config.get("recent_repos", [])
        
        assert result == []


class TestRecentBranches:
    """Test recent branches management."""

    def test_add_recent_branch_new_repo(self):
        """Test adding branch for new repository."""
        config = {"recent_branches": {}}
        repo_path = "/test/repo"
        branch = "feature-branch"
        
        add_recent_branch(config, repo_path, branch)
        
        assert config["recent_branches"][repo_path] == [branch]

    def test_add_recent_branch_existing_repo(self):
        """Test adding branch to existing repository."""
        config = {"recent_branches": {"/test/repo": ["main"]}}
        repo_path = "/test/repo"
        branch = "feature-branch"
        
        add_recent_branch(config, repo_path, branch)
        
        assert config["recent_branches"][repo_path] == ["feature-branch", "main"]

    def test_add_recent_branch_existing_branch(self):
        """Test adding existing branch moves it to front."""
        config = {"recent_branches": {"/test/repo": ["main", "feature-1", "feature-2"]}}
        repo_path = "/test/repo"
        branch = "feature-1"
        
        add_recent_branch(config, repo_path, branch)
        
        assert config["recent_branches"][repo_path] == ["feature-1", "main", "feature-2"]

    def test_add_recent_branch_max_limit(self):
        """Test adding branch respects maximum limit."""
        branches = [f"branch-{i}" for i in range(RECENT_BRANCHES_MAX)]
        config = {"recent_branches": {"/test/repo": branches}}
        repo_path = "/test/repo"
        new_branch = "new-branch"
        
        add_recent_branch(config, repo_path, new_branch)
        
        assert len(config["recent_branches"][repo_path]) == RECENT_BRANCHES_MAX
        assert config["recent_branches"][repo_path][0] == new_branch
        assert f"branch-{RECENT_BRANCHES_MAX-1}" not in config["recent_branches"][repo_path]

    def test_get_recent_branches_for_repo_exists(self):
        """Test getting recent branches for existing repository."""
        branches = ["main", "feature-1"]
        config = {"recent_branches": {"/test/repo": branches}}
        
        result = get_recent_branches_for_repo(config, "/test/repo")
        
        assert result == branches

    def test_get_recent_branches_for_repo_not_exists(self):
        """Test getting recent branches for non-existing repository."""
        config = {"recent_branches": {}}
        
        result = get_recent_branches_for_repo(config, "/test/repo")
        
        assert result == []

    def test_get_recent_branches_for_repo_empty(self):
        """Test getting recent branches for repository with empty list."""
        config = {"recent_branches": {"/test/repo": []}}
        
        result = get_recent_branches_for_repo(config, "/test/repo")
        
        assert result == []


