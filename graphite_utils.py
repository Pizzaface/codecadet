"""Graphite integration utilities."""

import subprocess
import shutil
from pathlib import Path
from typing import List, Optional


def find_graphite_cli() -> Optional[str]:
    """Find the Graphite CLI executable."""
    # Common locations for gt command
    possible_paths = [
        shutil.which("gt"),  # Standard PATH lookup
        str(Path.home() / ".nvm/versions/node/v20.17.0/bin/gt"),
        str(Path.home() / ".local/bin/gt"),
        str(Path.home() / "bin/gt"),
    ]
    
    for path in possible_paths:
        if path and Path(path).exists() and Path(path).is_file():
            return path
    
    return None


def is_graphite_repo(repo_path: Path) -> bool:
    """Check if a repository is initialized with Graphite."""
    try:
        gt_cmd = find_graphite_cli()
        if not gt_cmd:
            return False
            
        # Check if repo has graphite config
        result = subprocess.run(
            [gt_cmd, "--cwd", str(repo_path), "info", "--quiet"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def is_branch_in_stack(repo_path: Path, branch: str) -> bool:
    """Check if a branch is part of a Graphite stack."""
    try:
        gt_cmd = find_graphite_cli()
        if not gt_cmd:
            return False
            
        result = subprocess.run(
            [gt_cmd, "--cwd", str(repo_path), "info", branch, "--quiet"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_current_branch_info(repo_path: Path) -> dict:
    """Get information about the current branch from Graphite."""
    try:
        gt_cmd = find_graphite_cli()
        if not gt_cmd:
            return {}
            
        result = subprocess.run(
            [gt_cmd, "--cwd", str(repo_path), "info", "--quiet"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Parse the output for useful info
            lines = result.stdout.strip().split('\n')
            info = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.strip().lower()] = value.strip()
            return info
    except Exception:
        pass
    
    return {}


def run_graphite_command(repo_path: Path, command: List[str], allow_interactive: bool = False) -> tuple[bool, str]:
    """Run a Graphite command and return success status and output."""
    try:
        gt_cmd = find_graphite_cli()
        if not gt_cmd:
            return False, "Graphite CLI not found"
        
        full_cmd = [gt_cmd, "--cwd", str(repo_path)] + command
        
        # Handle interactive commands (like top when there are multiple branches)
        if allow_interactive:
            # For interactive commands, we might get a selection prompt
            # Try with --select flag for automated selection of first option
            if command[0] in ["top", "checkout"]:
                # Add --select flag to auto-select first option when there are multiple
                full_cmd.extend(["--select", "0"])
        
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip() or result.stderr.strip()
        
        # Handle the case where there are multiple top branches
        if result.returncode != 0 and "Multiple branches found" in output:
            # Try again with interactive selection disabled for now
            # The UI will handle this case by showing the error to the user
            return False, f"Multiple top branches found in stack. Please use the branch switcher to select a specific branch.\n\n{output}"
        
        return result.returncode == 0, output
        
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, f"Error: {str(e)}"


def get_stack_branches(repo_path: Path, branch: Optional[str] = None) -> List[str]:
    """Get all branches in the stack for the given branch (or current branch)."""
    try:
        gt_cmd = find_graphite_cli()
        if not gt_cmd:
            return []
            
        # Get the stack info using gt log
        cmd = [gt_cmd, "--cwd", str(repo_path), "log", "--short"]
        if branch:
            cmd.append(branch)
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # Parse the output to extract branch names
            branches = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('◯') and not line.startswith('│'):
                    # Extract branch name from the log output
                    parts = line.split()
                    if len(parts) > 0:
                        branch_name = parts[0].strip('◯○●').strip()
                        if branch_name and branch_name not in branches:
                            branches.append(branch_name)
            return branches
    except Exception:
        pass
    
    return []


def check_worktree_conflicts(repo_path: Path, worktrees_info: Any, target_branches: List[str]) -> dict:
    """Check if any target branches are currently checked out in other worktrees."""
    conflicts = {}
    
    for worktree in worktrees_info:
        if not worktree.branch:
            continue
            
        # Clean branch name
        branch_name = worktree.branch
        if branch_name.startswith("refs/heads/"):
            branch_name = branch_name[11:]
            
        # Check if this branch is in our target list
        if branch_name in target_branches:
            conflicts[branch_name] = {
                'worktree_path': worktree.path,
                'worktree_name': worktree.path.name,
                'is_main': worktree.is_main
            }
    
    return conflicts


def suggest_conflict_resolution(conflicts: dict, current_worktree: Path) -> List[str]:
    """Suggest ways to resolve worktree conflicts."""
    suggestions = []
    
    for branch, conflict_info in conflicts.items():
        worktree_path = conflict_info['worktree_path']
        worktree_name = conflict_info['worktree_name']
        
        if worktree_path == current_worktree:
            continue  # Skip current worktree
            
        if conflict_info['is_main']:
            suggestions.append(f"• Switch '{branch}' in main worktree to trunk/main")
        else:
            suggestions.append(f"• Switch '{branch}' in '{worktree_name}' worktree to a different branch")
    
    return suggestions


def run_safe_graphite_command(repo_path: Path, command: List[str], worktrees_info) -> tuple[bool, str, dict]:
    """Run a Graphite command with pre-flight conflict checking."""
    # Commands that might cause conflicts with worktrees
    conflict_prone_commands = ["restack", "sync", "modify", "squash", "fold"]
    
    conflicts = {}
    if any(cmd in conflict_prone_commands for cmd in command):
        # Get current branch to determine stack
        try:
            current_branch = None
            result = subprocess.run(
                ["git", "-C", str(repo_path), "branch", "--show-current"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current_branch = result.stdout.strip()
        except Exception:
            pass
        
        if current_branch:
            # Get all branches in the stack
            stack_branches = get_stack_branches(repo_path, current_branch)
            if stack_branches:
                conflicts = check_worktree_conflicts(repo_path, worktrees_info, stack_branches)
    
    # If no conflicts, run the command normally
    if not conflicts:
        success, output = run_graphite_command(repo_path, command)
        return success, output, {}
    
    # Return conflict information for UI to handle
    return False, f"Potential worktree conflicts detected for branches: {', '.join(conflicts.keys())}", conflicts


# Common Graphite commands that would be useful in the UI
GRAPHITE_COMMANDS = {
    # Navigation commands
    "up": {"cmd": ["up"], "desc": "Move up one branch in stack", "icon": "⬆️", "safe": True},
    "down": {"cmd": ["down"], "desc": "Move down one branch in stack", "icon": "⬇️", "safe": True},
    "top": {"cmd": ["top"], "desc": "Go to top of current stack", "icon": "🔝", "safe": True, "allow_interactive": True},
    "bottom": {"cmd": ["bottom"], "desc": "Go to bottom of current stack", "icon": "⬇️", "safe": True},
    
    # Stack management
    "log": {"cmd": ["log"], "desc": "Show stack visualization", "icon": "📊", "safe": True},
    "submit": {"cmd": ["submit"], "desc": "Submit current stack", "icon": "🚀", "safe": False},
    "sync": {"cmd": ["sync"], "desc": "Sync with remote", "icon": "🔄", "safe": False},
    "restack": {"cmd": ["restack"], "desc": "Rebase stack", "icon": "⚡", "safe": False},
    
    # Branch operations
    "create": {"cmd": ["create"], "desc": "Create new branch", "icon": "➕", "safe": True},
    "modify": {"cmd": ["modify"], "desc": "Modify current branch", "icon": "✏️", "safe": False},
    "checkout": {"cmd": ["checkout"], "desc": "Interactive checkout", "icon": "🔀", "safe": True, "allow_interactive": True},
    
    # Info commands
    "info": {"cmd": ["info"], "desc": "Show branch info", "icon": "ℹ️", "safe": True},
    "parent": {"cmd": ["parent"], "desc": "Show parent branch", "icon": "⬆️", "safe": True},
    "children": {"cmd": ["children"], "desc": "Show child branches", "icon": "⬇️", "safe": True},
}

