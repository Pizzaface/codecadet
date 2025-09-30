"""Tests for Git operations."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from git_utils import (
    which, run_git, ensure_repo_root, git_version_ok,
    list_worktrees, add_worktree, remove_worktree,
    list_branches
)
from models import WorktreeInfo


class TestUtilityFunctions:
    """Test utility functions."""

    @patch('shutil.which')
    def test_which_command_found(self, mock_which):
        """Test which function when command is found."""
        mock_which.return_value = '/usr/bin/git'
        result = which('git')
        assert result == '/usr/bin/git'
        mock_which.assert_called_once_with('git')

    @patch('shutil.which')
    def test_which_command_not_found(self, mock_which):
        """Test which function when command is not found."""
        mock_which.return_value = None
        result = which('nonexistent')
        assert result is None
        mock_which.assert_called_once_with('nonexistent')


class TestRunGit:
    """Test run_git function."""

    @patch('subprocess.run')
    def test_run_git_success(self, mock_run):
        """Test successful git command execution."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_git(['status'], cwd='/test/repo')
        
        assert result == mock_result
        mock_run.assert_called_once_with(
            ['git', 'status'],
            cwd='/test/repo',
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    @patch('subprocess.run')
    def test_run_git_file_not_found(self, mock_run):
        """Test git command when git is not found."""
        mock_run.side_effect = FileNotFoundError("git not found")
        
        with pytest.raises(RuntimeError, match="Git not found on PATH"):
            run_git(['status'])

    @patch('subprocess.run')
    def test_run_git_command_error(self, mock_run):
        """Test git command that fails."""
        error = subprocess.CalledProcessError(1, ['git', 'status'])
        error.stderr = "fatal: not a git repository"
        mock_run.side_effect = error
        
        with pytest.raises(RuntimeError, match="fatal: not a git repository"):
            run_git(['status'])

    @patch('subprocess.run')
    def test_run_git_no_check(self, mock_run):
        """Test git command with check=False."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = run_git(['status'], check=False)
        
        assert result == mock_result
        mock_run.assert_called_once_with(
            ['git', 'status'],
            cwd=None,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )


class TestEnsureRepoRoot:
    """Test ensure_repo_root function."""

    @patch('git_utils.run_git')
    def test_ensure_repo_root_success(self, mock_run_git):
        """Test getting repository root successfully."""
        mock_result = Mock()
        mock_result.stdout = "/home/user/repo\n"
        mock_run_git.return_value = mock_result

        result = ensure_repo_root(Path("/home/user/repo/subdir"))
        
        assert result == Path("/home/user/repo")
        mock_run_git.assert_called_once_with(["-C", "/home/user/repo/subdir", "rev-parse", "--show-toplevel"])

    @patch('git_utils.run_git')
    def test_ensure_repo_root_failure(self, mock_run_git):
        """Test ensure_repo_root when not in a git repository."""
        mock_run_git.side_effect = RuntimeError("fatal: not a git repository")
        
        with pytest.raises(RuntimeError, match="fatal: not a git repository"):
            ensure_repo_root(Path("/home/user/notrepo"))


class TestGitVersionOk:
    """Test git_version_ok function."""

    @patch('git_utils.run_git')
    def test_git_version_ok_sufficient(self, mock_run_git):
        """Test git version check with sufficient version."""
        mock_result = Mock()
        mock_result.stdout = "git version 2.30.0\n"
        mock_run_git.return_value = mock_result

        result = git_version_ok(2, 5)
        
        assert result is True
        mock_run_git.assert_called_once_with(["--version"])

    @patch('git_utils.run_git')
    def test_git_version_ok_insufficient(self, mock_run_git):
        """Test git version check with insufficient version."""
        mock_result = Mock()
        mock_result.stdout = "git version 2.4.0\n"
        mock_run_git.return_value = mock_result

        result = git_version_ok(2, 5)
        
        assert result is False

    @patch('git_utils.run_git')
    def test_git_version_ok_parse_error(self, mock_run_git):
        """Test git version check with unparseable version."""
        mock_result = Mock()
        mock_result.stdout = "invalid version string\n"
        mock_run_git.return_value = mock_result

        result = git_version_ok(2, 5)
        
        assert result is False

    @patch('git_utils.run_git')
    def test_git_version_ok_command_error(self, mock_run_git):
        """Test git version check when command fails."""
        mock_run_git.side_effect = RuntimeError("git not found")

        result = git_version_ok(2, 5)
        
        assert result is False


class TestListWorktrees:
    """Test list_worktrees function."""

    @patch('git_utils.run_git')
    def test_list_worktrees_success(self, mock_run_git):
        """Test listing worktrees successfully."""
        mock_result = Mock()
        mock_result.stdout = (
            "/home/user/repo\t(bare)\n"
            "/home/user/repo-main\tabc123\t[main]\n"
            "/home/user/repo-feature\tdef456\t[feature-branch]\n"
        )
        mock_run_git.return_value = mock_result

        result = list_worktrees(Path("/home/user/repo"))
        
        assert len(result) == 3
        
        # Check main worktree
        assert result[0].path == Path("/home/user/repo")
        assert result[0].head is None
        assert result[0].branch is None
        assert result[0].is_main is True
        
        # Check regular worktrees
        assert result[1].path == Path("/home/user/repo-main")
        assert result[1].head == "abc123"
        assert result[1].branch == "main"
        assert result[1].is_main is False

    @patch('git_utils.run_git')
    def test_list_worktrees_empty(self, mock_run_git):
        """Test listing worktrees when none exist."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run_git.return_value = mock_result

        result = list_worktrees(Path("/home/user/repo"))
        
        assert result == []

    @patch('git_utils.run_git')
    def test_list_worktrees_error(self, mock_run_git):
        """Test listing worktrees when command fails."""
        mock_run_git.side_effect = RuntimeError("not a git repository")

        with pytest.raises(RuntimeError, match="not a git repository"):
            list_worktrees(Path("/home/user/notrepo"))


class TestAddWorktree:
    """Test add_worktree function."""

    @patch('git_utils.run_git')
    def test_add_worktree_success(self, mock_run_git):
        """Test adding worktree successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_git.return_value = mock_result

        add_worktree(
            repo_root=Path("/home/user/repo"),
            new_path=Path("/home/user/repo-feature"),
            branch="feature-branch",
            base_ref=None
        )
        
        # Should call run_git twice: once to check if branch exists, once to add worktree
        assert mock_run_git.call_count == 2

    @patch('git_utils.run_git')
    def test_add_worktree_with_base_ref(self, mock_run_git):
        """Test adding worktree with base reference."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_git.return_value = mock_result

        add_worktree(
            repo_root=Path("/home/user/repo"),
            new_path=Path("/home/user/repo-feature"),
            branch="feature-branch",
            base_ref="origin/feature-branch"
        )
        
        # Should call run_git twice: once to check if branch exists, once to add worktree
        assert mock_run_git.call_count == 2

    @patch('git_utils.run_git')
    def test_add_worktree_error(self, mock_run_git):
        """Test adding worktree when command fails."""
        mock_run_git.side_effect = RuntimeError("branch already exists")

        with pytest.raises(RuntimeError, match="branch already exists"):
            add_worktree(
                repo_root=Path("/home/user/repo"),
                new_path=Path("/home/user/repo-feature"),
                branch="existing-branch",
                base_ref=None
            )


class TestRemoveWorktree:
    """Test remove_worktree function."""

    @patch('git_utils.run_git')
    def test_remove_worktree_success(self, mock_run_git):
        """Test removing worktree successfully."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_git.return_value = mock_result

        remove_worktree(
            repo_root=Path("/home/user/repo"),
            path=Path("/home/user/repo-feature")
        )
        
        mock_run_git.assert_called_once_with([
            "-C", "/home/user/repo",
            "worktree", "remove",
            "/home/user/repo-feature"
        ])

    @patch('git_utils.run_git')
    def test_remove_worktree_force(self, mock_run_git):
        """Test removing worktree with force option."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_git.return_value = mock_result

        remove_worktree(
            repo_root=Path("/home/user/repo"),
            path=Path("/home/user/repo-feature"),
            force=True
        )
        
        mock_run_git.assert_called_once_with([
            "-C", "/home/user/repo",
            "worktree", "remove",
            "--force",
            "/home/user/repo-feature"
        ])

    @patch('git_utils.run_git')
    def test_remove_worktree_error(self, mock_run_git):
        """Test removing worktree when command fails."""
        mock_run_git.side_effect = RuntimeError("worktree not found")

        with pytest.raises(RuntimeError, match="worktree not found"):
            remove_worktree(
                repo_root=Path("/home/user/repo"),
                path=Path("/home/user/repo-nonexistent")
            )


class TestBranchOperations:
    """Test branch-related operations."""

    @patch('git_utils.run_git')
    def test_get_current_branch_success(self, mock_run_git):
        """Test getting current branch successfully."""
        mock_result = Mock()
        mock_result.stdout = "main\n"
        mock_run_git.return_value = mock_result

        result = get_current_branch(Path("/home/user/repo"))
        
        assert result == "main"
        mock_run_git.assert_called_once_with([
            "-C", "/home/user/repo",
            "branch", "--show-current"
        ])

    @patch('git_utils.run_git')
    def test_get_current_branch_detached(self, mock_run_git):
        """Test getting current branch when in detached HEAD state."""
        mock_result = Mock()
        mock_result.stdout = "\n"
        mock_run_git.return_value = mock_result

        result = get_current_branch(Path("/home/user/repo"))
        
        assert result is None

    @patch('git_utils.run_git')
    def test_get_branches_success(self, mock_run_git):
        """Test getting all branches successfully."""
        mock_result = Mock()
        mock_result.stdout = "  feature-1\n* main\n  feature-2\n"
        mock_run_git.return_value = mock_result

        result = get_branches(Path("/home/user/repo"))
        
        assert result == ["feature-1", "main", "feature-2"]
        mock_run_git.assert_called_once_with([
            "-C", "/home/user/repo",
            "branch", "--format=%(refname:short)"
        ])

    @patch('git_utils.run_git')
    def test_get_recent_branches_success(self, mock_run_git):
        """Test getting recent branches successfully."""
        mock_result = Mock()
        mock_result.stdout = "main\nfeature-1\nfeature-2\n"
        mock_run_git.return_value = mock_result

        result = get_recent_branches(Path("/home/user/repo"), limit=3)
        
        assert result == ["main", "feature-1", "feature-2"]
        mock_run_git.assert_called_once_with([
            "-C", "/home/user/repo",
            "for-each-ref",
            "--sort=-committerdate",
            "--format=%(refname:short)",
            "--count=3",
            "refs/heads/"
        ])

    @patch('git_utils.run_git')
    def test_get_recent_branches_default_limit(self, mock_run_git):
        """Test getting recent branches with default limit."""
        mock_result = Mock()
        mock_result.stdout = "main\n"
        mock_run_git.return_value = mock_result

        result = get_recent_branches(Path("/home/user/repo"))
        
        mock_run_git.assert_called_once_with([
            "-C", "/home/user/repo",
            "for-each-ref",
            "--sort=-committerdate",
            "--format=%(refname:short)",
            "--count=10",
            "refs/heads/"
        ])


