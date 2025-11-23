"""Tests for the utils module."""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import Mock, MagicMock
from utils import (
    MockTerminalProcess,
    remove_path_entry,
    truncate_path_for_display,
    clean_branch_name,
    format_geometry_string,
    parse_geometry_string
)


class TestRemovePathEntry(unittest.TestCase):
    """Test remove_path_entry function."""

    def test_remove_single_entry(self):
        """Test removing a single entry from PATH."""
        path = "/usr/bin:/tmp:/usr/local/bin"
        result = remove_path_entry(path, "/tmp")
        self.assertEqual(result, "/usr/bin:/usr/local/bin")

    def test_remove_first_entry(self):
        """Test removing the first entry."""
        path = "/tmp:/usr/bin:/usr/local/bin"
        result = remove_path_entry(path, "/tmp")
        self.assertEqual(result, "/usr/bin:/usr/local/bin")

    def test_remove_last_entry(self):
        """Test removing the last entry."""
        path = "/usr/bin:/usr/local/bin:/tmp"
        result = remove_path_entry(path, "/tmp")
        self.assertEqual(result, "/usr/bin:/usr/local/bin")

    def test_remove_nonexistent_entry(self):
        """Test removing a non-existent entry."""
        path = "/usr/bin:/usr/local/bin"
        result = remove_path_entry(path, "/tmp")
        self.assertEqual(result, path)

    def test_remove_from_empty_string(self):
        """Test removing from an empty string."""
        result = remove_path_entry("", "/tmp")
        self.assertEqual(result, "")

    def test_remove_empty_entry(self):
        """Test removing an empty entry."""
        path = "/usr/bin:/usr/local/bin"
        result = remove_path_entry(path, "")
        self.assertEqual(result, path)

    def test_remove_multiple_occurrences(self):
        """Test removing multiple occurrences of the same entry."""
        path = "/tmp:/usr/bin:/tmp:/usr/local/bin"
        result = remove_path_entry(path, "/tmp")
        self.assertEqual(result, "/usr/bin:/usr/local/bin")


class TestTruncatePathForDisplay(unittest.TestCase):
    """Test truncate_path_for_display function."""

    def test_truncate_long_path(self):
        """Test truncating a path longer than max_length."""
        path = Path("/very/long/path/to/some/file.txt")
        result = truncate_path_for_display(path, 20)
        self.assertLessEqual(len(result), 20)
        self.assertTrue(result.startswith("..."))

    def test_no_truncation_needed(self):
        """Test a path that doesn't need truncation."""
        path = Path("/short/path")
        result = truncate_path_for_display(path, 50)
        self.assertEqual(result, str(path))

    def test_exact_max_length(self):
        """Test a path that is exactly max_length."""
        path = Path("/exact")
        result = truncate_path_for_display(path, len(str(path)))
        self.assertEqual(result, str(path))

    def test_truncation_preserves_end(self):
        """Test that truncation preserves the end of the path."""
        path = Path("/very/long/path/to/file.txt")
        result = truncate_path_for_display(path, 20)
        self.assertTrue(result.endswith("file.txt"))


class TestCleanBranchName(unittest.TestCase):
    """Test clean_branch_name function."""

    def test_remove_refs_heads_prefix(self):
        """Test removing refs/heads/ prefix."""
        branch = "refs/heads/feature/new-feature"
        result = clean_branch_name(branch)
        self.assertEqual(result, "feature/new-feature")

    def test_remove_remotes_origin_prefix(self):
        """Test removing remotes/origin/ prefix."""
        branch = "remotes/origin/main"
        result = clean_branch_name(branch)
        self.assertEqual(result, "main")

    def test_clean_branch_without_prefix(self):
        """Test cleaning a branch name without prefix."""
        branch = "main"
        result = clean_branch_name(branch)
        self.assertEqual(result, "main")

    def test_empty_branch_name(self):
        """Test cleaning an empty branch name."""
        result = clean_branch_name("")
        self.assertEqual(result, "")

    def test_none_branch_name(self):
        """Test cleaning None returns None."""
        result = clean_branch_name(None)
        self.assertIsNone(result)


class TestFormatGeometryString(unittest.TestCase):
    """Test format_geometry_string function."""

    def test_basic_geometry(self):
        """Test formatting basic geometry."""
        result = format_geometry_string(1000, 600, 100, 100)
        self.assertEqual(result, "1000x600+100+100")

    def test_zero_position(self):
        """Test geometry with zero position."""
        result = format_geometry_string(800, 600, 0, 0)
        self.assertEqual(result, "800x600+0+0")

    def test_large_values(self):
        """Test geometry with large values."""
        result = format_geometry_string(1920, 1080, 500, 300)
        self.assertEqual(result, "1920x1080+500+300")


class TestParseGeometryString(unittest.TestCase):
    """Test parse_geometry_string function."""

    def test_parse_valid_geometry(self):
        """Test parsing a valid geometry string."""
        result = parse_geometry_string("1000x600+100+100")
        self.assertEqual(result, (1000, 600, 100, 100))

    def test_parse_zero_position(self):
        """Test parsing geometry with zero position."""
        result = parse_geometry_string("800x600+0+0")
        self.assertEqual(result, (800, 600, 0, 0))

    def test_parse_invalid_format(self):
        """Test parsing an invalid format returns None."""
        result = parse_geometry_string("invalid")
        self.assertIsNone(result)

    def test_parse_missing_plus(self):
        """Test parsing geometry without + returns None."""
        result = parse_geometry_string("1000x600")
        self.assertIsNone(result)

    def test_parse_missing_x(self):
        """Test parsing geometry without x returns None."""
        result = parse_geometry_string("1000+600+100+100")
        self.assertIsNone(result)

    def test_parse_non_numeric(self):
        """Test parsing geometry with non-numeric values returns None."""
        result = parse_geometry_string("abcxdef+ghi+jkl")
        self.assertIsNone(result)

    def test_round_trip(self):
        """Test that format and parse are inverse operations."""
        original = (1024, 768, 50, 50)
        formatted = format_geometry_string(*original)
        parsed = parse_geometry_string(formatted)
        self.assertEqual(parsed, original)


class TestMockTerminalProcess(unittest.TestCase):
    """Test MockTerminalProcess class."""

    def test_poll_with_web_terminal(self):
        """Test poll with web terminal widget."""
        # Mock web terminal widget with bridge
        widget = Mock()
        widget.bridge = Mock()
        widget.bridge.process_pid = 12345

        process = MockTerminalProcess(widget)

        # Should return None when process is running
        # We can't actually test os.kill without a real process,
        # but we can test the structure
        self.assertIsNotNone(process.widget)

    def test_poll_with_pty_terminal(self):
        """Test poll with PTY terminal widget."""
        # Mock PTY terminal widget
        widget = Mock()
        widget.process_pid = 12345

        process = MockTerminalProcess(widget)
        self.assertIsNotNone(process.widget)

    def test_poll_no_process(self):
        """Test poll with widget that has no process."""
        widget = Mock(spec=[])  # No process_pid or bridge attribute
        process = MockTerminalProcess(widget)

        # Should return 0 when no process info available
        result = process.poll()
        self.assertEqual(result, 0)

    def test_terminate_with_cleanup(self):
        """Test terminate calls cleanup method."""
        widget = Mock()
        widget.cleanup = Mock()

        process = MockTerminalProcess(widget)
        process.terminate()

        widget.cleanup.assert_called_once()

    def test_terminate_with_private_cleanup(self):
        """Test terminate calls _cleanup method."""
        widget = Mock()
        widget._cleanup = Mock()
        delattr(widget, 'cleanup')  # Remove cleanup attribute

        process = MockTerminalProcess(widget)
        process.terminate()

        widget._cleanup.assert_called_once()

    def test_terminate_no_cleanup(self):
        """Test terminate when widget has no cleanup method."""
        widget = Mock(spec=[])  # No cleanup or _cleanup attribute

        process = MockTerminalProcess(widget)
        # Should not raise an error
        process.terminate()


if __name__ == '__main__':
    unittest.main()
