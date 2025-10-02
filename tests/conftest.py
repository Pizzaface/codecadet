"""Pytest configuration and fixtures for codecadet tests."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_git_repo(temp_dir: Path) -> Path:
    """Create a temporary git repository for testing."""
    import subprocess

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True)

    # Create initial commit
    readme_file = temp_dir / "README.md"
    readme_file.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "README.md"], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

    return temp_dir


@pytest.fixture
def sample_config() -> dict:
    """Provide a sample configuration for testing."""
    return {
        "recent_repos": [],
        "recent_branches": {},
        "agents": {"default": {"command": "claude", "args": []}},
        "default_agent": "default",
        "terminal": {"shell": "/bin/bash"},
    }


@pytest.fixture
def config_file(temp_dir: Path, sample_config: dict) -> Path:
    """Create a temporary config file for testing."""
    import json

    config_path = temp_dir / "config.json"
    config_path.write_text(json.dumps(sample_config, indent=2))
    return config_path
