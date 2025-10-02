"""Tests for git utility functions."""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from git_utils import (
    run_git,
    ensure_repo_root,
    git_version_ok,
    add_worktree,
    remove_worktree,
    checkout_branch,
    prune_worktrees
)


class TestRunGit:
    """Tests for run_git function."""
    
    def test_run_git_success(self, temp_git_repo: Path):
        """Test successful git command execution."""
        result = run_git(["status", "--porcelain"], cwd=temp_git_repo)
        
        assert result.returncode == 0
        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)
    
    def test_run_git_failure(self, temp_git_repo: Path):
        """Test git command that fails."""
        with pytest.raises(subprocess.CalledProcessError):
            run_git(["invalid-command"], cwd=temp_git_repo, check=True)
    
    def test_run_git_no_check(self, temp_git_repo: Path):
        """Test git command failure without check=True."""
        result = run_git(["invalid-command"], cwd=temp_git_repo, check=False)
        
        assert result.returncode != 0
        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)
    
    def test_run_git_no_cwd(self):
        """Test git command without specifying cwd."""
        # This should work if we're in a git repo or fail gracefully
        result = run_git(["--version"], check=False)
        
        # Git version should always work
        assert result.returncode == 0
        assert "git version" in result.stdout


class TestEnsureRepoRoot:
    """Tests for ensure_repo_root function."""
    
    def test_ensure_repo_root_valid_repo(self, temp_git_repo: Path):
        """Test ensure_repo_root with valid git repository."""
        repo_root = ensure_repo_root(temp_git_repo)
        
        assert repo_root == temp_git_repo
        assert (repo_root / ".git").exists()
    
    def test_ensure_repo_root_subdirectory(self, temp_git_repo: Path):
        """Test ensure_repo_root from subdirectory of git repo."""
        subdir = temp_git_repo / "subdir"
        subdir.mkdir()
        
        repo_root = ensure_repo_root(subdir)
        
        assert repo_root == temp_git_repo
        assert (repo_root / ".git").exists()
    
    def test_ensure_repo_root_not_a_repo(self, temp_dir: Path):
        """Test ensure_repo_root with directory that's not a git repo."""
        with pytest.raises(ValueError, match="not a git repository"):
            ensure_repo_root(temp_dir)
    
    def test_ensure_repo_root_nonexistent_path(self, temp_dir: Path):
        """Test ensure_repo_root with non-existent path."""
        nonexistent = temp_dir / "nonexistent"
        
        with pytest.raises(ValueError, match="not a git repository"):
            ensure_repo_root(nonexistent)


class TestGitVersionOk:
    """Tests for git_version_ok function."""
    
    @patch('git_utils.run_git')
    def test_git_version_ok_sufficient(self, mock_run_git):
        """Test git_version_ok with sufficient version."""
        mock_result = MagicMock()
        mock_result.stdout = "git version 2.30.0\n"
        mock_run_git.return_value = mock_result
        
        assert git_version_ok(2, 25) is True
        mock_run_git.assert_called_once_with(["--version"])
    
    @patch('git_utils.run_git')
    def test_git_version_ok_insufficient(self, mock_run_git):
        """Test git_version_ok with insufficient version."""
        mock_result = MagicMock()
        mock_result.stdout = "git version 2.20.0\n"
        mock_run_git.return_value = mock_result
        
        assert git_version_ok(2, 25) is False
    
    @patch('git_utils.run_git')
    def test_git_version_ok_exact_match(self, mock_run_git):
        """Test git_version_ok with exact version match."""
        mock_result = MagicMock()
        mock_result.stdout = "git version 2.25.0\n"
        mock_run_git.return_value = mock_result
        
        assert git_version_ok(2, 25) is True
    
    @patch('git_utils.run_git')
    def test_git_version_ok_parse_error(self, mock_run_git):
        """Test git_version_ok with unparseable version output."""
        mock_result = MagicMock()
        mock_result.stdout = "invalid version output\n"
        mock_run_git.return_value = mock_result
        
        assert git_version_ok(2, 25) is False
    
    @patch('git_utils.run_git')
    def test_git_version_ok_command_failure(self, mock_run_git):
        """Test git_version_ok when git command fails."""
        mock_run_git.side_effect = subprocess.CalledProcessError(1, ["git", "--version"])
        
        assert git_version_ok(2, 25) is False


class TestAddWorktree:
    """Tests for add_worktree function."""
    
    def test_add_worktree_success(self, temp_git_repo: Path):
        """Test successful worktree addition."""
        worktree_path = temp_git_repo.parent / "test-worktree"
        branch_name = "test-branch"
        
        # Create a test branch first
        run_git(["checkout", "-b", branch_name], cwd=temp_git_repo)
        run_git(["checkout", "main"], cwd=temp_git_repo, check=False)  # Switch back
        
        # Add worktree
        add_worktree(temp_git_repo, worktree_path, branch_name)
        
        # Verify worktree was created
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()
        
        # Verify it's listed in worktrees
        result = run_git(["worktree", "list"], cwd=temp_git_repo)
        assert str(worktree_path) in result.stdout
    
    def test_add_worktree_new_branch(self, temp_git_repo: Path):
        """Test adding worktree with new branch creation."""
        worktree_path = temp_git_repo.parent / "new-branch-worktree"
        branch_name = "new-feature"
        
        # Add worktree with new branch
        add_worktree(temp_git_repo, worktree_path, branch_name, create_branch=True)
        
        # Verify worktree was created
        assert worktree_path.exists()
        
        # Verify branch exists
        result = run_git(["branch", "-a"], cwd=temp_git_repo)
        assert branch_name in result.stdout


class TestRemoveWorktree:
    """Tests for remove_worktree function."""
    
    def test_remove_worktree_success(self, temp_git_repo: Path):
        """Test successful worktree removal."""
        worktree_path = temp_git_repo.parent / "remove-test-worktree"
        branch_name = "remove-test-branch"
        
        # Create worktree first
        run_git(["checkout", "-b", branch_name], cwd=temp_git_repo)
        run_git(["checkout", "main"], cwd=temp_git_repo, check=False)
        add_worktree(temp_git_repo, worktree_path, branch_name)
        
        # Remove worktree
        remove_worktree(temp_git_repo, worktree_path)
        
        # Verify worktree was removed
        result = run_git(["worktree", "list"], cwd=temp_git_repo)
        assert str(worktree_path) not in result.stdout
    
    def test_remove_worktree_force(self, temp_git_repo: Path):
        """Test forced worktree removal."""
        worktree_path = temp_git_repo.parent / "force-remove-worktree"
        branch_name = "force-remove-branch"
        
        # Create worktree
        run_git(["checkout", "-b", branch_name], cwd=temp_git_repo)
        run_git(["checkout", "main"], cwd=temp_git_repo, check=False)
        add_worktree(temp_git_repo, worktree_path, branch_name)
        
        # Create uncommitted changes to make removal require force
        test_file = worktree_path / "test.txt"
        test_file.write_text("uncommitted changes")
        
        # Remove with force
        remove_worktree(temp_git_repo, worktree_path, force=True)
        
        # Verify worktree was removed
        result = run_git(["worktree", "list"], cwd=temp_git_repo)
        assert str(worktree_path) not in result.stdout


class TestCheckoutBranch:
    """Tests for checkout_branch function."""
    
    def test_checkout_branch_existing(self, temp_git_repo: Path):
        """Test checking out existing branch."""
        branch_name = "test-checkout"
        
        # Create branch
        run_git(["checkout", "-b", branch_name], cwd=temp_git_repo)
        run_git(["checkout", "main"], cwd=temp_git_repo, check=False)
        
        # Checkout the branch
        checkout_branch(temp_git_repo, branch_name)
        
        # Verify we're on the correct branch
        result = run_git(["branch", "--show-current"], cwd=temp_git_repo)
        assert result.stdout.strip() == branch_name
    
    def test_checkout_branch_create_new(self, temp_git_repo: Path):
        """Test creating and checking out new branch."""
        branch_name = "new-checkout-branch"
        
        # Checkout new branch
        checkout_branch(temp_git_repo, branch_name, create=True)
        
        # Verify we're on the new branch
        result = run_git(["branch", "--show-current"], cwd=temp_git_repo)
        assert result.stdout.strip() == branch_name
        
        # Verify branch exists in branch list
        result = run_git(["branch"], cwd=temp_git_repo)
        assert branch_name in result.stdout


class TestPruneWorktrees:
    """Tests for prune_worktrees function."""
    
    def test_prune_worktrees_no_stale(self, temp_git_repo: Path):
        """Test pruning when no stale worktrees exist."""
        # This should run without error even with no stale worktrees
        prune_worktrees(temp_git_repo)
        
        # Verify command completed (no exception raised)
        assert True
    
    def test_prune_worktrees_with_stale(self, temp_git_repo: Path):
        """Test pruning with stale worktrees."""
        worktree_path = temp_git_repo.parent / "stale-worktree"
        branch_name = "stale-branch"
        
        # Create worktree
        run_git(["checkout", "-b", branch_name], cwd=temp_git_repo)
        run_git(["checkout", "main"], cwd=temp_git_repo, check=False)
        add_worktree(temp_git_repo, worktree_path, branch_name)
        
        # Manually remove the worktree directory to make it stale
        import shutil
        shutil.rmtree(worktree_path)
        
        # Prune should clean up the stale reference
        prune_worktrees(temp_git_repo)
        
        # Verify stale worktree is no longer listed
        result = run_git(["worktree", "list"], cwd=temp_git_repo)
        assert str(worktree_path) not in result.stdout


class TestIntegration:
    """Integration tests combining multiple git operations."""
    
    def test_worktree_lifecycle(self, temp_git_repo: Path):
        """Test complete worktree lifecycle: create, use, remove."""
        worktree_path = temp_git_repo.parent / "lifecycle-worktree"
        branch_name = "lifecycle-branch"
        
        # Ensure we're in a valid repo
        repo_root = ensure_repo_root(temp_git_repo)
        assert repo_root == temp_git_repo
        
        # Create new branch and worktree
        checkout_branch(repo_root, branch_name, create=True)
        checkout_branch(repo_root, "main")  # Switch back to main
        add_worktree(repo_root, worktree_path, branch_name)
        
        # Verify worktree exists and is functional
        assert worktree_path.exists()
        result = run_git(["status"], cwd=worktree_path)
        assert result.returncode == 0
        
        # Clean up
        remove_worktree(repo_root, worktree_path)
        prune_worktrees(repo_root)
        
        # Verify cleanup
        result = run_git(["worktree", "list"], cwd=repo_root)
        assert str(worktree_path) not in result.stdout
