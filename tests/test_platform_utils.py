"""Tests for cross-platform utilities."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from platform_utils import Platform, Shell, TerminalLauncher


class TestPlatform:
    """Tests for Platform class."""

    def test_is_windows(self):
        """Test Windows detection."""
        with patch('sys.platform', 'win32'):
            assert Platform.is_windows() is True
            assert Platform.is_macos() is False
            assert Platform.is_linux() is False
            assert Platform.is_unix() is False

    def test_is_macos(self):
        """Test macOS detection."""
        with patch('sys.platform', 'darwin'):
            assert Platform.is_windows() is False
            assert Platform.is_macos() is True
            assert Platform.is_linux() is False
            assert Platform.is_unix() is True

    def test_is_linux(self):
        """Test Linux detection."""
        with patch('sys.platform', 'linux'):
            assert Platform.is_windows() is False
            assert Platform.is_macos() is False
            assert Platform.is_linux() is True
            assert Platform.is_unix() is True


class TestShell:
    """Tests for Shell class."""

    def test_get_user_shell_from_env(self):
        """Test shell detection from SHELL environment variable."""
        with patch.dict(os.environ, {'SHELL': '/bin/bash'}):
            with patch('os.path.exists', return_value=True):
                with patch('sys.platform', 'linux'):
                    shell = Shell.get_user_shell()
                    assert shell == '/bin/bash'

    def test_get_user_shell_from_pwd(self):
        """Test shell detection from password database."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.platform', 'linux'):
                # Mock pwd module
                import importlib
                pwd_mock = MagicMock()
                pwd_mock.getpwuid.return_value.pw_shell = '/bin/zsh'

                with patch('os.path.exists', return_value=True):
                    with patch('os.getuid', return_value=1000):
                        with patch.dict('sys.modules', {'pwd': pwd_mock}):
                            shell = Shell.get_user_shell()
                            # It should attempt to use pwd
                            assert shell in ['/bin/zsh', '/bin/bash', '/bin/sh']

    def test_get_user_shell_fallback(self):
        """Test shell detection fallback to common shells."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.platform', 'linux'):
                # Mock os.path.exists to return True for /bin/bash
                def exists_side_effect(path):
                    return path == '/bin/bash'

                with patch('os.path.exists', side_effect=exists_side_effect):
                    with patch('importlib.import_module', side_effect=ImportError):
                        shell = Shell.get_user_shell()
                        assert shell == '/bin/bash'

    def test_get_user_shell_windows(self):
        """Test shell detection on Windows."""
        with patch('sys.platform', 'win32'):
            with patch('shutil.which', return_value='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'):
                shell = Shell.get_user_shell()
                assert 'powershell' in shell.lower() or shell == 'cmd.exe'

    def test_get_shell_args_bash(self):
        """Test getting shell arguments for bash."""
        args = Shell.get_shell_args('/bin/bash', 'echo hello')
        assert args == ['/bin/bash', '-c', 'echo hello']

    def test_get_shell_args_zsh(self):
        """Test getting shell arguments for zsh."""
        args = Shell.get_shell_args('/bin/zsh', 'ls -la')
        assert args == ['/bin/zsh', '-c', 'ls -la']

    def test_get_shell_args_cmd(self):
        """Test getting shell arguments for Windows cmd."""
        args = Shell.get_shell_args('C:\\Windows\\System32\\cmd.exe', 'dir')
        assert args == ['C:\\Windows\\System32\\cmd.exe', '/c', 'dir']

    def test_get_shell_args_powershell(self):
        """Test getting shell arguments for PowerShell."""
        args = Shell.get_shell_args('powershell.exe', 'Get-ChildItem')
        assert args == ['powershell.exe', '-Command', 'Get-ChildItem']


class TestTerminalLauncher:
    """Tests for TerminalLauncher class."""

    def test_find_available_terminal_linux(self):
        """Test finding available terminal on Linux."""
        with patch('sys.platform', 'linux'):
            with patch('shutil.which', return_value='/usr/bin/gnome-terminal'):
                terminal = TerminalLauncher.find_available_terminal()
                assert terminal is not None
                assert terminal[0] == '/usr/bin/gnome-terminal'

    def test_find_available_terminal_not_linux(self):
        """Test that find_available_terminal returns None on non-Linux."""
        with patch('sys.platform', 'darwin'):
            terminal = TerminalLauncher.find_available_terminal()
            assert terminal is None

    def test_launch_windows(self):
        """Test launching terminal on Windows."""
        with patch('sys.platform', 'win32'):
            with patch('shutil.which', return_value=None):
                with patch('subprocess.Popen') as mock_popen:
                    result = TerminalLauncher.launch(Path('/test/path'))
                    assert result is True
                    mock_popen.assert_called_once()
                    call_args = mock_popen.call_args[0][0]
                    assert 'cmd' in call_args

    def test_launch_macos(self):
        """Test launching terminal on macOS."""
        with patch('sys.platform', 'darwin'):
            with patch('subprocess.Popen') as mock_popen:
                result = TerminalLauncher.launch(Path('/test/path'))
                assert result is True
                mock_popen.assert_called_once()
                call_args = mock_popen.call_args[0][0]
                assert 'osascript' in call_args

    def test_launch_linux(self):
        """Test launching terminal on Linux."""
        with patch('sys.platform', 'linux'):
            with patch('shutil.which', return_value='/usr/bin/gnome-terminal'):
                with patch('subprocess.Popen') as mock_popen:
                    result = TerminalLauncher.launch(Path('/test/path'))
                    assert result is True
                    mock_popen.assert_called_once()

    def test_launch_linux_no_terminal(self):
        """Test launching terminal on Linux when no terminal is found."""
        with patch('sys.platform', 'linux'):
            with patch('shutil.which', return_value=None):
                result = TerminalLauncher.launch(Path('/test/path'))
                assert result is False

    def test_launch_with_command(self):
        """Test launching terminal with a command."""
        with patch('sys.platform', 'linux'):
            with patch('shutil.which', return_value='/usr/bin/gnome-terminal'):
                with patch('subprocess.Popen') as mock_popen:
                    result = TerminalLauncher.launch(Path('/test/path'), 'python script.py')
                    assert result is True
                    mock_popen.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
