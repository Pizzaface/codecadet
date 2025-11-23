"""Tests for the terminal command builder module."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from terminal_command_builder import TerminalCommandBuilder


class TestTerminalCommandBuilder(unittest.TestCase):
    """Test TerminalCommandBuilder class."""

    def setUp(self):
        """Set up test builder."""
        self.builder = TerminalCommandBuilder()

    def test_default_platform(self):
        """Test that default platform is detected."""
        self.assertIsNotNone(self.builder.platform)
        self.assertIsInstance(self.builder.platform, str)

    def test_custom_platform(self):
        """Test creating builder with custom platform."""
        darwin_builder = TerminalCommandBuilder('darwin')
        self.assertEqual(darwin_builder.platform, 'darwin')

        linux_builder = TerminalCommandBuilder('linux')
        self.assertEqual(linux_builder.platform, 'linux')


class TestGeometryBuilding(unittest.TestCase):
    """Test geometry string building."""

    def setUp(self):
        """Set up test builder."""
        self.builder = TerminalCommandBuilder()

    def test_build_geometry_basic(self):
        """Test building basic geometry string."""
        geometry = self.builder.build_geometry_string(
            container_width=800,
            container_height=600,
            char_width=7,
            char_height=14,
            padding=20,
            min_cols=40,
            min_rows=10
        )

        # Should be in format "COLSxROWS"
        self.assertIn('x', geometry)
        parts = geometry.split('x')
        self.assertEqual(len(parts), 2)

        cols, rows = map(int, parts)
        self.assertGreaterEqual(cols, 40)
        self.assertGreaterEqual(rows, 10)

    def test_geometry_respects_minimums(self):
        """Test that geometry respects minimum values."""
        geometry = self.builder.build_geometry_string(
            container_width=10,  # Very small
            container_height=10,
            char_width=7,
            char_height=14,
            padding=20,
            min_cols=40,
            min_rows=10
        )

        cols, rows = map(int, geometry.split('x'))
        self.assertEqual(cols, 40)  # Should use minimum
        self.assertEqual(rows, 10)  # Should use minimum

    def test_geometry_calculation(self):
        """Test geometry calculation is correct."""
        # 800 width - 20 padding = 780
        # 780 / 7 char_width = 111 cols
        geometry = self.builder.build_geometry_string(
            container_width=800,
            container_height=600,
            char_width=7,
            char_height=14,
            padding=20,
            min_cols=40,
            min_rows=10
        )

        cols, rows = map(int, geometry.split('x'))
        expected_cols = (800 - 20) // 7
        expected_rows = (600 - 20) // 14
        self.assertEqual(cols, expected_cols)
        self.assertEqual(rows, expected_rows)


class TestPathCleanupSnippet(unittest.TestCase):
    """Test path cleanup snippet generation."""

    def setUp(self):
        """Set up test builder."""
        self.builder = TerminalCommandBuilder('linux')

    def test_path_cleanup_with_venv(self):
        """Test path cleanup snippet when venv is set."""
        self.builder.set_app_venv_bin(Path('/test/venv/bin'))
        snippet = self.builder._build_path_cleanup_snippet()

        self.assertIsInstance(snippet, str)
        self.assertGreater(len(snippet), 0)
        self.assertIn('APP_VENV_BIN', snippet)
        self.assertIn('/test/venv/bin', snippet)

    def test_path_cleanup_without_venv(self):
        """Test path cleanup snippet when venv is not set."""
        snippet = self.builder._build_path_cleanup_snippet()
        self.assertEqual(snippet, "")

    def test_path_cleanup_escaping(self):
        """Test that path cleanup escapes special characters."""
        self.builder.set_app_venv_bin(Path('/path/with$dollar'))
        snippet = self.builder._build_path_cleanup_snippet()

        # Should escape $ to \$
        self.assertIn('\\$', snippet)


class TestPathAppendSnippet(unittest.TestCase):
    """Test path append snippet generation."""

    def setUp(self):
        """Set up test builder."""
        self.builder = TerminalCommandBuilder()

    def test_path_append_snippet(self):
        """Test path append snippet generation."""
        snippet = self.builder._build_path_append_snippet()

        self.assertIsInstance(snippet, str)
        self.assertGreater(len(snippet), 0)
        self.assertIn('PATH_EXTRAS', snippet)
        self.assertIn('.local/bin', snippet)
        self.assertIn('.cargo/bin', snippet)


class TestProfileSourceSnippet(unittest.TestCase):
    """Test profile source snippet generation."""

    def test_darwin_profile_source(self):
        """Test macOS profile sourcing."""
        builder = TerminalCommandBuilder('darwin')
        snippet = builder._build_profile_source_snippet()

        self.assertIsInstance(snippet, str)
        self.assertIn('zshrc', snippet)
        self.assertIn('brew', snippet)
        self.assertIn('/opt/homebrew/bin/brew', snippet)

    def test_linux_profile_source(self):
        """Test Linux profile sourcing."""
        builder = TerminalCommandBuilder('linux')
        snippet = builder._build_profile_source_snippet()

        self.assertIsInstance(snippet, str)
        self.assertIn('bashrc', snippet)
        self.assertIn('bash_profile', snippet)
        self.assertNotIn('brew', snippet)


class TestLocaleSetup(unittest.TestCase):
    """Test locale setup snippet generation."""

    def setUp(self):
        """Set up test builder."""
        self.builder = TerminalCommandBuilder()

    def test_locale_setup_snippet(self):
        """Test locale setup snippet."""
        snippet = self.builder._build_locale_setup_snippet()

        self.assertIsInstance(snippet, str)
        self.assertIn('LANG=en_US.UTF-8', snippet)
        self.assertIn('LC_ALL=en_US.UTF-8', snippet)
        self.assertIn('LC_CTYPE=en_US.UTF-8', snippet)
        self.assertIn('PYTHONIOENCODING=utf-8', snippet)


class TestShellCommand(unittest.TestCase):
    """Test shell command detection."""

    def test_darwin_uses_zsh(self):
        """Test that macOS uses zsh."""
        builder = TerminalCommandBuilder('darwin')
        shell = builder._get_shell_command()
        self.assertEqual(shell, 'zsh')

    def test_linux_uses_bash(self):
        """Test that Linux uses bash."""
        builder = TerminalCommandBuilder('linux')
        shell = builder._get_shell_command()
        self.assertEqual(shell, 'bash')


class TestAgentLaunchCommand(unittest.TestCase):
    """Test complete agent launch command building."""

    def test_build_command_basic(self):
        """Test building a basic agent launch command."""
        builder = TerminalCommandBuilder('darwin')
        builder.set_app_venv_bin(Path('/app/venv/bin'))

        command = builder.build_agent_launch_command(
            working_dir=Path('/test/repo'),
            agent_command='claude'
        )

        self.assertIsInstance(command, str)
        self.assertGreater(len(command), 0)

    def test_command_contains_agent(self):
        """Test that command contains the agent command."""
        builder = TerminalCommandBuilder()
        command = builder.build_agent_launch_command(
            working_dir=Path('/test/repo'),
            agent_command='claude'
        )

        self.assertIn('claude', command)

    def test_command_contains_working_dir(self):
        """Test that command contains working directory."""
        builder = TerminalCommandBuilder()
        command = builder.build_agent_launch_command(
            working_dir=Path('/test/repo'),
            agent_command='claude'
        )

        self.assertIn('/test/repo', command)

    def test_command_contains_locale(self):
        """Test that command sets up locale."""
        builder = TerminalCommandBuilder()
        command = builder.build_agent_launch_command(
            working_dir=Path('/test/repo'),
            agent_command='claude'
        )

        self.assertIn('LANG=en_US.UTF-8', command)
        self.assertIn('LC_ALL=en_US.UTF-8', command)

    def test_command_sources_profiles(self):
        """Test that command sources profile files."""
        builder = TerminalCommandBuilder('darwin')
        command = builder.build_agent_launch_command(
            working_dir=Path('/test/repo'),
            agent_command='claude'
        )

        self.assertIn('zshrc', command)

    def test_command_ends_with_interactive_shell(self):
        """Test that command ends with interactive shell."""
        builder = TerminalCommandBuilder('darwin')
        command = builder.build_agent_launch_command(
            working_dir=Path('/test/repo'),
            agent_command='claude'
        )

        self.assertIn('exec zsh -i', command)

    def test_command_escapes_special_chars(self):
        """Test that command properly escapes special characters."""
        builder = TerminalCommandBuilder()
        command = builder.build_agent_launch_command(
            working_dir=Path('/test/path with spaces'),
            agent_command='claude'
        )

        # shlex.quote should handle spaces
        self.assertIn("'", command)  # Should use quotes


class TestSetAppVenvBin(unittest.TestCase):
    """Test setting app venv bin directory."""

    def test_set_app_venv_bin(self):
        """Test setting the app venv bin path."""
        builder = TerminalCommandBuilder()
        venv_path = Path('/test/venv/bin')

        builder.set_app_venv_bin(venv_path)

        self.assertEqual(builder._app_venv_bin, str(venv_path))

    def test_set_app_venv_bin_affects_cleanup(self):
        """Test that setting venv bin affects cleanup snippet."""
        builder = TerminalCommandBuilder('linux')

        # Without venv set
        snippet1 = builder._build_path_cleanup_snippet()
        self.assertEqual(snippet1, "")

        # With venv set
        builder.set_app_venv_bin(Path('/test/venv/bin'))
        snippet2 = builder._build_path_cleanup_snippet()
        self.assertGreater(len(snippet2), 0)


if __name__ == '__main__':
    unittest.main()
