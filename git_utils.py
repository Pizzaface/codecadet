"""Git operations for Worktree Manager."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Any

from models import WorktreeInfo


def which(cmd: str) -> str | None:
    """Find command in PATH."""
    return shutil.which(cmd)


def run_git(args: List[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command with safe argument passing."""
    cmd = ["git"] + list(args)
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return cp
    except FileNotFoundError:
        raise RuntimeError("Git not found on PATH.")
    except subprocess.CalledProcessError as e:
        # surface stderr to caller
        raise RuntimeError(e.stderr.strip() or str(e))


def ensure_repo_root(path: Path) -> Path:
    """Return the repo root for any path inside a Git repo."""
    cp = run_git(["-C", str(path), "rev-parse", "--show-toplevel"])
    return Path(cp.stdout.strip())


def git_version_ok(min_major: int = 2, min_minor: int = 5) -> bool:
    """Check if Git version meets minimum requirements."""
    try:
        v = run_git(["--version"], check=False).stdout.strip()
        parts = v.split()
        if len(parts) >= 3:
            nums = parts[2].split(".")
            major = int(nums[0])
            minor = int(nums[1])
            return (major > min_major) or (major == min_major and minor >= min_minor)
    except (ValueError, IndexError, AttributeError) as e:
        logging.warning(f"Failed to parse git version: {e}")
        pass
    return False


def parse_porcelain_list(text: str) -> list[WorktreeInfo]:
    """Parse `git worktree list --porcelain`."""
    results = []
    block = {}
    for line in text.splitlines():
        if not line.strip():
            if block:
                results.append(_block_to_info(block))
                block = {}
            continue
        key, *rest = line.split(" ", 1)
        val = rest[0] if rest else ""
        block.setdefault(key, []).append(val)
    if block:
        results.append(_block_to_info(block))
    return results


def _block_to_info(block: dict) -> WorktreeInfo:
    """Convert a parsed block to WorktreeInfo."""
    path = Path(block.get("worktree", [""])[0])
    head = (block.get("HEAD", [None])[0]) or None
    branch = None
    if "branch" in block:
        br = block["branch"][0]
        if br and br != "(detached)":
            branch = br
    locked = "locked" in block
    prunable = "prunable" in block
    return WorktreeInfo(path=path, head=head, branch=branch,
                        locked=locked, prunable=prunable, is_main=False)


def list_worktrees(repo_root: Path) -> list[WorktreeInfo]:
    """List all worktrees in a repository."""
    cp = run_git(["-C", str(repo_root), "worktree", "list", "--porcelain"])
    infos = parse_porcelain_list(cp.stdout)
    for info in infos:
        try:
            if info.path.resolve() == repo_root.resolve():
                info.is_main = True
        except (OSError, RuntimeError) as e:
            logging.warning(f"Failed to resolve path for worktree {info.path}: {e}")
            pass
    return infos


def add_worktree(repo_root: Path, new_path: Path, branch: str | None, base_ref: str | None) -> None:
    """Add a new worktree."""
    args = ["-C", str(repo_root), "worktree", "add"]
    if branch:
        exists = run_git(["-C", str(repo_root), "rev-parse", "--verify", f"refs/heads/{branch}"], check=False)
        if exists.returncode != 0:
            args += ["-b", branch]
    args.append(str(new_path))
    if base_ref:
        args.append(base_ref)
    run_git(args)


def remove_worktree(repo_root: Path, wt_path: Path, force: bool = False) -> None:
    """Remove a worktree."""
    args = ["-C", str(repo_root), "worktree", "remove"]
    if force:
        args.append("-f")
    args.append(str(wt_path))
    run_git(args)


def prune_worktrees(repo_root: Path):
    """Prune stale worktrees."""
    run_git(["-C", str(repo_root), "worktree", "prune", "-v"])


def checkout_branch(worktree_path: Path, branch: str) -> None:
    """Switch to a different branch in the given worktree."""
    run_git(["-C", str(worktree_path), "checkout", branch])


def list_branches(repo_root: Path) -> list[str]:
    """Get list of all branches in the repository."""
    cp = run_git(["-C", str(repo_root), "branch", "-a"])
    branches = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if line.startswith("* "):
            line = line[2:]
        if line.startswith("remotes/origin/"):
            line = line[15:]  # Remove "remotes/origin/"
        if line and line not in branches and not line.startswith("HEAD ->"):
            branches.append(line)
    return sorted(set(branches))









