"""Basic tests to verify test structure is working."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# Mock PySide6 to avoid GUI dependencies in headless environment
sys.modules["PySide6"] = MagicMock()
sys.modules["PySide6.QtWidgets"] = MagicMock()
sys.modules["PySide6.QtCore"] = MagicMock()

from config import load_config, save_config
from git_utils import ensure_repo_root


class TestBasicFunctionality:
    """Basic tests for critical functions mentioned in the task."""

    def test_load_config_basic(self, temp_dir: Path):
        """Basic test for load_config function."""
        # Create a simple config file
        config_file = temp_dir / "test_config.json"
        test_config = {"test": "value", "recent_repos": []}
        config_file.write_text(json.dumps(test_config))

        # Test loading
        result = load_config(config_file)
        assert isinstance(result, dict)
        assert "recent_repos" in result

    def test_save_config_basic(self, temp_dir: Path):
        """Basic test for save_config function."""
        config_file = temp_dir / "save_test.json"
        test_config = {"test": "save", "recent_repos": []}

        # Test saving
        save_config(test_config, config_file)

        # Verify file was created
        assert config_file.exists()
        saved_data = json.loads(config_file.read_text())
        assert saved_data["test"] == "save"

    def test_ensure_repo_root_basic(self, temp_git_repo: Path):
        """Basic test for ensure_repo_root function."""
        # Test with valid git repo
        result = ensure_repo_root(temp_git_repo)
        assert isinstance(result, Path)
        assert result == temp_git_repo

    def test_ensure_repo_root_invalid(self, temp_dir: Path):
        """Test ensure_repo_root with non-git directory."""
        with pytest.raises(ValueError):
            ensure_repo_root(temp_dir)


def test_pytest_is_working():
    """Simple test to verify pytest is working."""
    assert True


def test_fixtures_are_working(temp_dir: Path, temp_git_repo: Path):
    """Test that our fixtures are working properly."""
    assert temp_dir.exists()
    assert temp_git_repo.exists()
    assert (temp_git_repo / ".git").exists()
