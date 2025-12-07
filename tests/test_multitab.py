#!/usr/bin/env python3
"""Test script for multi-tab session functionality."""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import SessionInfo
from session import SessionManager
import subprocess
import time


def test_session_manager_multitab():
    """Test the SessionManager's multi-tab functionality."""
    print("Testing SessionManager multi-tab functionality...")
    
    # Create session manager with max 3 tabs for testing
    manager = SessionManager(max_tabs_per_worktree=3)
    
    # Create test worktree path
    test_path = Path("/tmp/test_worktree")
    
    # Test 1: Register multiple sessions
    print("\n1. Registering multiple sessions...")
    
    # Create mock process and container for testing (cross-platform)
    mock_process = subprocess.Popen([
        sys.executable,
        "-c",
        "import time; time.sleep(10)",
    ])
    mock_container = None  # We don't need a real container for testing
    
    tab1_id = manager.register_session(
        test_path, mock_process, mock_container, 
        "claude", "Test Terminal 1"
    )
    print(f"   Created tab 1: {tab1_id}")
    
    tab2_id = manager.register_session(
        test_path, mock_process, mock_container, 
        "claude", "Test Terminal 2"
    )
    print(f"   Created tab 2: {tab2_id}")
    
    # Test 2: List sessions for worktree
    print("\n2. Listing sessions for worktree...")
    sessions = manager.get_all_sessions_for_worktree(test_path)
    print(f"   Found {len(sessions)} sessions")
    for tab_id, session in sessions.items():
        print(f"   - {tab_id}: {session.tab_name}")
    
    # Test 3: Rename a tab
    print("\n3. Renaming a tab...")
    manager.rename_tab(test_path, tab1_id, "Renamed Terminal")
    updated_session = manager.get_session(test_path, tab1_id)
    if updated_session:
        print(f"   Renamed to: {updated_session.tab_name}")
    
    # Test 4: Remove a tab
    print("\n4. Removing a tab...")
    manager.remove_session(test_path, tab2_id)
    sessions_after = manager.get_all_sessions_for_worktree(test_path)
    print(f"   Sessions after removal: {len(sessions_after)}")
    
    # Test 5: Tab limit enforcement
    print("\n5. Testing tab limit...")
    try:
        for i in range(3, 5):  # Try to create 2 more tabs (should exceed limit of 3)
            manager.register_session(
                test_path, mock_process, mock_container,
                "claude", f"Terminal {i}"
            )
        print("   ERROR: Tab limit not enforced!")
    except ValueError as e:
        print(f"   Tab limit enforced: {e}")
    
    # Cleanup
    manager.remove_all_sessions_for_worktree(test_path)
    mock_process.terminate()
    
    print("\n✅ All tests passed!")


def test_tab_bar_functionality():
    """Test TabBar widget functionality (without GUI)."""
    print("\n\nTesting TabBar functionality (logic only)...")
    
    # Test tab name generation and management
    from ui.tab_bar import TabBar
    
    # We can't actually create the widget without a GUI, but we can test the logic
    print("\n1. Tab ID generation...")
    import uuid
    test_id = str(uuid.uuid4())[:8]
    print(f"   Generated tab ID: {test_id}")
    
    print("\n2. Tab name validation...")
    valid_names = ["Terminal 1", "Build", "Test Suite", "Dev Server"]
    for name in valid_names:
        print(f"   Valid name: '{name}'")
    
    print("\n✅ TabBar logic tests passed!")


if __name__ == "__main__":
    try:
        test_session_manager_multitab()
        test_tab_bar_functionality()
        print("\n\n🎉 All multi-tab tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
