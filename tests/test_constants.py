"""Tests for the constants module."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import constants


class TestTerminalConstants(unittest.TestCase):
    """Test terminal configuration constants."""

    def test_terminal_char_dimensions(self):
        """Test terminal character dimensions are positive integers."""
        self.assertIsInstance(constants.TERMINAL_CHAR_WIDTH, int)
        self.assertIsInstance(constants.TERMINAL_CHAR_HEIGHT, int)
        self.assertGreater(constants.TERMINAL_CHAR_WIDTH, 0)
        self.assertGreater(constants.TERMINAL_CHAR_HEIGHT, 0)

    def test_terminal_minimums(self):
        """Test terminal minimum dimensions."""
        self.assertGreaterEqual(constants.TERMINAL_MIN_COLS, 1)
        self.assertGreaterEqual(constants.TERMINAL_MIN_ROWS, 1)

    def test_terminal_padding(self):
        """Test terminal container padding."""
        self.assertGreaterEqual(constants.TERMINAL_CONTAINER_PADDING, 0)


class TestWindowConstants(unittest.TestCase):
    """Test window configuration constants."""

    def test_default_window_dimensions(self):
        """Test default window size constants."""
        self.assertGreater(constants.DEFAULT_WINDOW_WIDTH, 0)
        self.assertGreater(constants.DEFAULT_WINDOW_HEIGHT, 0)

    def test_minimum_window_dimensions(self):
        """Test minimum window size constants."""
        self.assertGreater(constants.MIN_WINDOW_WIDTH, 0)
        self.assertGreater(constants.MIN_WINDOW_HEIGHT, 0)

    def test_minimum_less_than_default(self):
        """Test that minimum sizes are less than or equal to defaults."""
        self.assertLessEqual(constants.MIN_WINDOW_WIDTH, constants.DEFAULT_WINDOW_WIDTH)
        self.assertLessEqual(constants.MIN_WINDOW_HEIGHT, constants.DEFAULT_WINDOW_HEIGHT)


class TestSplitterConstants(unittest.TestCase):
    """Test splitter proportion constants."""

    def test_splitter_proportions(self):
        """Test splitter initial widths are positive."""
        self.assertGreater(constants.SIDEBAR_INITIAL_WIDTH, 0)
        self.assertGreater(constants.TERMINAL_PANE_INITIAL_WIDTH, 0)


class TestNotificationConstants(unittest.TestCase):
    """Test notification configuration constants."""

    def test_notification_rate_limit(self):
        """Test notification rate limit is a positive number."""
        self.assertIsInstance(constants.NOTIFICATION_SOUND_RATE_LIMIT_SECONDS, float)
        self.assertGreater(constants.NOTIFICATION_SOUND_RATE_LIMIT_SECONDS, 0)

    def test_notification_volume(self):
        """Test notification volume is between 0 and 1."""
        self.assertGreaterEqual(constants.NOTIFICATION_SOUND_VOLUME, 0)
        self.assertLessEqual(constants.NOTIFICATION_SOUND_VOLUME, 1)


class TestApplicationConstants(unittest.TestCase):
    """Test application configuration constants."""

    def test_app_title(self):
        """Test app title is a non-empty string."""
        self.assertIsInstance(constants.APP_TITLE, str)
        self.assertGreater(len(constants.APP_TITLE), 0)

    def test_app_version(self):
        """Test app version is defined."""
        self.assertIsInstance(constants.APP_VERSION, str)
        self.assertGreater(len(constants.APP_VERSION), 0)

    def test_app_about_text(self):
        """Test about text is defined."""
        self.assertIsInstance(constants.APP_ABOUT_TEXT, str)
        self.assertGreater(len(constants.APP_ABOUT_TEXT), 0)


class TestStatusConstants(unittest.TestCase):
    """Test status message constants."""

    def test_status_messages(self):
        """Test status messages are non-empty strings."""
        self.assertIsInstance(constants.STATUS_READY, str)
        self.assertIsInstance(constants.STATUS_NO_SESSION, str)
        self.assertGreater(len(constants.STATUS_READY), 0)
        self.assertGreater(len(constants.STATUS_NO_SESSION), 0)


class TestLocaleConstants(unittest.TestCase):
    """Test locale configuration constants."""

    def test_default_locale(self):
        """Test default locale is a valid format."""
        self.assertIsInstance(constants.DEFAULT_LOCALE, str)
        self.assertIn("UTF-8", constants.DEFAULT_LOCALE)


class TestDeveloperPathConstants(unittest.TestCase):
    """Test developer tool path constants."""

    def test_common_developer_paths(self):
        """Test common developer paths are defined."""
        self.assertIsInstance(constants.COMMON_DEVELOPER_PATHS, list)
        self.assertGreater(len(constants.COMMON_DEVELOPER_PATHS), 0)

    def test_all_paths_are_strings(self):
        """Test all developer paths are strings."""
        for path in constants.COMMON_DEVELOPER_PATHS:
            self.assertIsInstance(path, str)
            self.assertGreater(len(path), 0)


class TestIconConstants(unittest.TestCase):
    """Test icon constants."""

    def test_icon_constants_defined(self):
        """Test that icon constants are defined."""
        icons = [
            constants.ICON_FOLDER,
            constants.ICON_FILE,
            constants.ICON_SUCCESS,
            constants.ICON_DELETE,
            constants.ICON_CLEAN,
            constants.ICON_SETTINGS,
            constants.ICON_ROBOT,
            constants.ICON_GRAPHITE,
            constants.ICON_WARNING
        ]

        for icon in icons:
            self.assertIsInstance(icon, str)
            self.assertGreater(len(icon), 0)  # Non-empty string (emojis can be 1-2 chars)
            self.assertLessEqual(len(icon), 2)  # Most emojis are 1-2 characters


class TestButtonPrefixConstants(unittest.TestCase):
    """Test button prefix constants."""

    def test_button_prefixes(self):
        """Test button prefix constants are defined."""
        prefixes = [
            constants.BUTTON_PREFIX_RUN,
            constants.BUTTON_PREFIX_EXTERNAL,
            constants.BUTTON_PREFIX_STOP
        ]

        for prefix in prefixes:
            self.assertIsInstance(prefix, str)
            self.assertGreater(len(prefix), 0)


class TestEnvironmentVariableConstants(unittest.TestCase):
    """Test environment variable name constants."""

    def test_env_var_names(self):
        """Test environment variable names are uppercase strings."""
        env_vars = [
            constants.ENV_VAR_VIRTUAL_ENV,
            constants.ENV_VAR_POETRY_ACTIVE,
            constants.ENV_VAR_PATH,
            constants.ENV_VAR_LANG,
            constants.ENV_VAR_LC_ALL,
            constants.ENV_VAR_LC_CTYPE,
            constants.ENV_VAR_PYTHONIOENCODING
        ]

        for var in env_vars:
            self.assertIsInstance(var, str)
            self.assertEqual(var, var.upper())  # Should be uppercase


class TestGitConstants(unittest.TestCase):
    """Test Git-related constants."""

    def test_git_branch_prefixes(self):
        """Test Git branch prefix constants."""
        self.assertEqual(constants.GIT_BRANCH_PREFIX_REFS_HEADS, "refs/heads/")
        self.assertEqual(constants.GIT_BRANCH_PREFIX_REMOTES_ORIGIN, "remotes/origin/")


class TestAttentionIndicatorConstants(unittest.TestCase):
    """Test attention indicator constants."""

    def test_attention_indicator(self):
        """Test attention indicator constants are defined."""
        self.assertIsInstance(constants.ATTENTION_INDICATOR_COLOR, str)
        self.assertIsInstance(constants.ATTENTION_INDICATOR_CHAR, str)
        self.assertTrue(constants.ATTENTION_INDICATOR_COLOR.startswith("#"))
        self.assertEqual(len(constants.ATTENTION_INDICATOR_CHAR), 1)


if __name__ == '__main__':
    unittest.main()
