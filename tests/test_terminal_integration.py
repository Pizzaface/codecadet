"""Integration tests for terminal functionality across different operating systems.

These tests verify that terminal integration works correctly on macOS, Linux,
and Windows by mocking platform-specific behaviors.
"""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import unittest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from terminal_command_builder import TerminalCommandBuilder
from constants import (
    TERMINAL_CHAR_WIDTH, TERMINAL_CHAR_HEIGHT, TERMINAL_MIN_COLS,
    TERMINAL_MIN_ROWS, TERMINAL_CONTAINER_PADDING, DEFAULT_LOCALE
)


class TestMacOSTerminalIntegration(unittest.TestCase):
    """Test terminal integration on macOS (darwin platform)."""

    def setUp(self):
        """Set up macOS terminal builder."""
        self.builder = TerminalCommandBuilder('darwin')
        self.test_repo = Path('/Users/test/projects/myrepo')
        self.venv_path = Path('/Users/test/codecadet/.venv/bin')

    def test_macos_uses_zsh_shell(self):
        """Verify macOS uses zsh as the shell."""
        self.assertEqual(self.builder._get_shell_command(), 'zsh')

    def test_macos_sources_zsh_profiles(self):
        """Verify macOS sources zsh profile files."""
        snippet = self.builder._build_profile_source_snippet()

        # Should source zsh-specific files
        self.assertIn('zshrc', snippet)
        self.assertIn('zshenv', snippet)
        self.assertIn('zprofile', snippet)

        # Should include Homebrew setup
        self.assertIn('brew', snippet)
        self.assertIn('/opt/homebrew/bin/brew', snippet)
        self.assertIn('/usr/local/bin/brew', snippet)

    def test_macos_command_structure(self):
        """Test complete command structure for macOS."""
        self.builder.set_app_venv_bin(self.venv_path)
        command = self.builder.build_agent_launch_command(
            self.test_repo, 'claude'
        )

        # Should contain all required elements
        self.assertIn('zsh', command)
        self.assertIn('claude', command)
        self.assertIn(str(self.test_repo), command)
        self.assertIn('zshrc', command)
        self.assertIn('brew', command)
        self.assertIn(DEFAULT_LOCALE, command)

        # Should end with interactive shell
        self.assertIn('exec zsh -i', command)

    def test_macos_path_cleanup(self):
        """Test PATH cleanup on macOS."""
        self.builder.set_app_venv_bin(self.venv_path)
        snippet = self.builder._build_path_cleanup_snippet()

        # Should contain APP_VENV_BIN variable (path will be escaped)
        self.assertIn('APP_VENV_BIN', snippet)
        self.assertIn('APP_VENV_BIN=', snippet)

        # Should use awk for PATH manipulation
        self.assertIn('awk', snippet)

    def test_macos_homebrew_paths_included(self):
        """Verify Homebrew paths are included in PATH."""
        snippet = self.builder._build_path_append_snippet()

        self.assertIn('/opt/homebrew/bin', snippet)
        self.assertIn('/opt/homebrew/sbin', snippet)

    def test_macos_complete_integration(self):
        """Full integration test for macOS terminal launch."""
        self.builder.set_app_venv_bin(self.venv_path)
        command = self.builder.build_agent_launch_command(
            self.test_repo, 'claude --verbose'
        )

        # Verify command is a valid shell command
        self.assertIsInstance(command, str)
        self.assertGreater(len(command), 100)

        # Verify order of operations
        # 1. PATH cleanup should come first
        self.assertLess(
            command.find('APP_VENV_BIN'),
            command.find('zshrc')
        )

        # 2. Profile sourcing
        self.assertLess(
            command.find('zshrc'),
            command.find('claude')
        )

        # 3. cd and run agent
        self.assertIn(f'cd', command)
        self.assertIn('claude --verbose', command)

        # 4. Interactive shell at end
        self.assertTrue(command.endswith('exec zsh -i'))


class TestLinuxTerminalIntegration(unittest.TestCase):
    """Test terminal integration on Linux."""

    def setUp(self):
        """Set up Linux terminal builder."""
        self.builder = TerminalCommandBuilder('linux')
        self.test_repo = Path('/home/test/projects/myrepo')
        self.venv_path = Path('/home/test/codecadet/.venv/bin')

    def test_linux_uses_bash_shell(self):
        """Verify Linux uses bash as the shell."""
        self.assertEqual(self.builder._get_shell_command(), 'bash')

    def test_linux_sources_bash_profiles(self):
        """Verify Linux sources bash profile files."""
        snippet = self.builder._build_profile_source_snippet()

        # Should source bash-specific files
        self.assertIn('bashrc', snippet)
        self.assertIn('bash_profile', snippet)
        self.assertIn('/etc/profile', snippet)

        # Should NOT include Homebrew (Linux doesn't typically use it)
        self.assertNotIn('brew', snippet)

    def test_linux_command_structure(self):
        """Test complete command structure for Linux."""
        self.builder.set_app_venv_bin(self.venv_path)
        command = self.builder.build_agent_launch_command(
            self.test_repo, 'claude'
        )

        # Should contain all required elements
        self.assertIn('bash', command)
        self.assertIn('claude', command)
        self.assertIn(str(self.test_repo), command)
        self.assertIn('bashrc', command)
        self.assertIn(DEFAULT_LOCALE, command)

        # Should end with interactive shell
        self.assertIn('exec bash -i', command)

    def test_linux_common_tool_paths(self):
        """Verify common Linux tool paths are included."""
        snippet = self.builder._build_path_append_snippet()

        # Common Linux paths
        self.assertIn('.local/bin', snippet)
        self.assertIn('.cargo/bin', snippet)
        self.assertIn('/usr/local/bin', snippet)

    def test_linux_xterm_geometry_calculation(self):
        """Test xterm geometry calculation for Linux."""
        geometry = self.builder.build_geometry_string(
            container_width=1024,
            container_height=768,
            char_width=TERMINAL_CHAR_WIDTH,
            char_height=TERMINAL_CHAR_HEIGHT,
            padding=TERMINAL_CONTAINER_PADDING,
            min_cols=TERMINAL_MIN_COLS,
            min_rows=TERMINAL_MIN_ROWS
        )

        # Should be in format COLSxROWS
        self.assertRegex(geometry, r'^\d+x\d+$')

        cols, rows = map(int, geometry.split('x'))

        # Expected: (1024-20)/7 = 143 cols, (768-20)/14 = 53 rows
        expected_cols = (1024 - TERMINAL_CONTAINER_PADDING) // TERMINAL_CHAR_WIDTH
        expected_rows = (768 - TERMINAL_CONTAINER_PADDING) // TERMINAL_CHAR_HEIGHT

        self.assertEqual(cols, expected_cols)
        self.assertEqual(rows, expected_rows)

    def test_linux_complete_integration(self):
        """Full integration test for Linux terminal launch."""
        self.builder.set_app_venv_bin(self.venv_path)
        command = self.builder.build_agent_launch_command(
            self.test_repo, 'claude --model sonnet'
        )

        # Verify command structure
        self.assertIsInstance(command, str)
        self.assertGreater(len(command), 100)

        # Verify order of operations matches Linux expectations
        self.assertIn('bash_profile', command)
        self.assertIn('claude --model sonnet', command)
        self.assertTrue(command.endswith('exec bash -i'))


class TestWindowsCompatibility(unittest.TestCase):
    """Test Windows compatibility (even though full support may be limited)."""

    def test_windows_platform_detection(self):
        """Test that Windows platform is handled."""
        builder = TerminalCommandBuilder('win32')
        self.assertEqual(builder.platform, 'win32')

    def test_windows_no_path_cleanup(self):
        """Verify PATH cleanup is skipped on Windows."""
        builder = TerminalCommandBuilder('win32')
        builder.set_app_venv_bin(Path('C:\\Users\\test\\venv\\Scripts'))

        # Windows should return empty cleanup snippet
        snippet = builder._build_path_cleanup_snippet()
        self.assertEqual(snippet, "")

    def test_windows_falls_back_to_bash(self):
        """Verify Windows falls back to bash for shell."""
        builder = TerminalCommandBuilder('win32')
        shell = builder._get_shell_command()

        # Should use bash (Git Bash, WSL, etc.)
        self.assertEqual(shell, 'bash')


class TestCrossPlatformLocaleSetup(unittest.TestCase):
    """Test that locale setup is consistent across platforms."""

    def test_locale_same_across_platforms(self):
        """Verify locale setup is identical on all platforms."""
        darwin_builder = TerminalCommandBuilder('darwin')
        linux_builder = TerminalCommandBuilder('linux')
        windows_builder = TerminalCommandBuilder('win32')

        darwin_locale = darwin_builder._build_locale_setup_snippet()
        linux_locale = linux_builder._build_locale_setup_snippet()
        windows_locale = windows_builder._build_locale_setup_snippet()

        # All should be identical
        self.assertEqual(darwin_locale, linux_locale)
        self.assertEqual(linux_locale, windows_locale)

        # Should contain UTF-8 settings
        self.assertIn('LANG=en_US.UTF-8', darwin_locale)
        self.assertIn('LC_ALL=en_US.UTF-8', darwin_locale)
        self.assertIn('PYTHONIOENCODING=utf-8', darwin_locale)


class TestPlatformSpecificPathHandling(unittest.TestCase):
    """Test platform-specific path handling and escaping."""

    def test_macos_path_with_spaces(self):
        """Test macOS handles paths with spaces correctly."""
        builder = TerminalCommandBuilder('darwin')
        repo_path = Path('/Users/test user/My Projects/app')

        command = builder.build_agent_launch_command(repo_path, 'claude')

        # Path should be quoted (shlex.quote adds quotes)
        self.assertIn("'", command)

    def test_linux_path_with_special_chars(self):
        """Test Linux handles paths with special characters."""
        builder = TerminalCommandBuilder('linux')
        repo_path = Path('/home/test/projects/my-app$test')

        command = builder.build_agent_launch_command(repo_path, 'claude')

        # Special chars should be escaped/quoted
        self.assertIn(str(repo_path), command.replace("'", ""))

    def test_path_cleanup_escapes_special_chars(self):
        """Test that PATH cleanup properly escapes special characters."""
        builder = TerminalCommandBuilder('linux')
        venv_with_special = Path('/home/test/my$app/.venv/bin')

        builder.set_app_venv_bin(venv_with_special)
        snippet = builder._build_path_cleanup_snippet()

        # Dollar sign should be escaped
        self.assertIn('\\$', snippet)


class TestEnvironmentVariableHandling(unittest.TestCase):
    """Test environment variable setup across platforms."""

    def test_all_env_vars_exported(self):
        """Verify all required environment variables are exported."""
        builder = TerminalCommandBuilder('linux')
        command = builder.build_agent_launch_command(
            Path('/test/repo'), 'claude'
        )

        required_env_vars = [
            'LANG=',
            'LC_ALL=',
            'LC_CTYPE=',
            'PYTHONIOENCODING='
        ]

        for env_var in required_env_vars:
            self.assertIn(env_var, command,
                         f"Environment variable {env_var} not found in command")

    def test_utf8_encoding_set(self):
        """Verify UTF-8 encoding is set for all locale variables."""
        builder = TerminalCommandBuilder('darwin')
        locale_snippet = builder._build_locale_setup_snippet()

        # All locale vars should use UTF-8
        self.assertIn('en_US.UTF-8', locale_snippet)
        self.assertIn('utf-8', locale_snippet.lower())


class TestCommandOrderingAndStructure(unittest.TestCase):
    """Test that commands are built in the correct order."""

    def test_path_cleanup_before_profile_source(self):
        """PATH cleanup should happen before sourcing profiles."""
        builder = TerminalCommandBuilder('darwin')
        builder.set_app_venv_bin(Path('/app/venv/bin'))

        command = builder.build_agent_launch_command(
            Path('/test/repo'), 'claude'
        )

        cleanup_pos = command.find('APP_VENV_BIN')
        profile_pos = command.find('zshrc')

        # Cleanup should come before profile sourcing
        self.assertLess(cleanup_pos, profile_pos,
                       "PATH cleanup should occur before profile sourcing")

    def test_path_cleanup_after_profile_source(self):
        """PATH should be cleaned again after sourcing profiles."""
        builder = TerminalCommandBuilder('linux')
        builder.set_app_venv_bin(Path('/app/venv/bin'))

        command = builder.build_agent_launch_command(
            Path('/test/repo'), 'claude'
        )

        # There should be two cleanup snippets (APP_VENV_BIN appears 3 times per cleanup)
        cleanup_count = command.count('APP_VENV_BIN')
        self.assertEqual(cleanup_count, 6,
                        "Should have PATH cleanup before AND after profile sourcing (3 occurrences each)")

    def test_locale_set_before_agent_launch(self):
        """Locale should be set before launching agent."""
        builder = TerminalCommandBuilder('linux')
        command = builder.build_agent_launch_command(
            Path('/test/repo'), 'claude'
        )

        locale_pos = command.find('LANG=')
        agent_pos = command.find('claude')

        self.assertLess(locale_pos, agent_pos,
                       "Locale should be set before agent launch")

    def test_cd_to_repo_before_agent(self):
        """Should cd to repository before launching agent."""
        builder = TerminalCommandBuilder('darwin')
        repo = Path('/test/my-repo')

        command = builder.build_agent_launch_command(repo, 'claude')

        cd_pos = command.find('cd')
        agent_pos = command.find('claude')

        self.assertLess(cd_pos, agent_pos,
                       "Should cd to repository before launching agent")

    def test_interactive_shell_at_end(self):
        """Interactive shell should be the last command."""
        for platform in ['darwin', 'linux', 'win32']:
            builder = TerminalCommandBuilder(platform)
            command = builder.build_agent_launch_command(
                Path('/test/repo'), 'claude'
            )

            shell = builder._get_shell_command()
            expected_end = f'exec {shell} -i'

            self.assertTrue(command.endswith(expected_end),
                           f"{platform}: Command should end with '{expected_end}'")


class TestGeometryCalculationAcrossPlatforms(unittest.TestCase):
    """Test geometry calculation works consistently across platforms."""

    def test_geometry_consistent_across_platforms(self):
        """Geometry calculation should be platform-independent."""
        darwin_builder = TerminalCommandBuilder('darwin')
        linux_builder = TerminalCommandBuilder('linux')

        darwin_geom = darwin_builder.build_geometry_string(
            800, 600, 7, 14, 20, 40, 10
        )
        linux_geom = linux_builder.build_geometry_string(
            800, 600, 7, 14, 20, 40, 10
        )

        # Should be identical
        self.assertEqual(darwin_geom, linux_geom)

    def test_minimum_geometry_enforced_all_platforms(self):
        """Minimum geometry should be enforced on all platforms."""
        for platform in ['darwin', 'linux', 'win32']:
            builder = TerminalCommandBuilder(platform)

            # Try with very small container
            geometry = builder.build_geometry_string(
                container_width=50,
                container_height=50,
                char_width=7,
                char_height=14,
                padding=20,
                min_cols=80,
                min_rows=24
            )

            cols, rows = map(int, geometry.split('x'))

            # Should use minimums despite small container
            self.assertEqual(cols, 80, f"{platform}: Should enforce min cols")
            self.assertEqual(rows, 24, f"{platform}: Should enforce min rows")


if __name__ == '__main__':
    unittest.main()
