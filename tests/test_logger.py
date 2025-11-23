"""Tests for the logger module."""

import sys
from pathlib import Path
import logging
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from logger import setup_logger, setup_file_logger, get_logger


class TestSetupLogger(unittest.TestCase):
    """Test setup_logger function."""

    def test_setup_logger_basic(self):
        """Test basic logger setup."""
        logger = setup_logger('test_logger')

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'test_logger')

    def test_logger_has_handlers(self):
        """Test that logger has handlers."""
        logger = setup_logger('test_logger_handlers')

        self.assertGreater(len(logger.handlers), 0)

    def test_logger_level(self):
        """Test that logger level is set correctly."""
        logger = setup_logger('test_logger_level', logging.DEBUG)

        self.assertEqual(logger.level, logging.DEBUG)

    def test_logger_default_level(self):
        """Test that default logger level is INFO."""
        logger = setup_logger('test_logger_default')

        self.assertEqual(logger.level, logging.INFO)

    def test_no_duplicate_handlers(self):
        """Test that calling setup_logger twice doesn't add duplicate handlers."""
        logger1 = setup_logger('test_logger_dup')
        handler_count1 = len(logger1.handlers)

        logger2 = setup_logger('test_logger_dup')
        handler_count2 = len(logger2.handlers)

        self.assertEqual(handler_count1, handler_count2)
        self.assertIs(logger1, logger2)  # Should return same logger instance


class TestSetupFileLogger(unittest.TestCase):
    """Test setup_file_logger function."""

    def _close_logger_handlers(self, logger):
        """Close all handlers for a logger to prevent file locks on Windows."""
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)

    def test_setup_file_logger_basic(self):
        """Test basic file logger setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            logger = setup_file_logger('test_file_logger', log_file)

            self.assertIsInstance(logger, logging.Logger)
            self.assertEqual(logger.name, 'test_file_logger')

            # Close handlers before cleanup
            self._close_logger_handlers(logger)

    def test_file_logger_creates_file(self):
        """Test that file logger creates the log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            logger = setup_file_logger('test_file_logger_file', log_file)

            # Write a log message
            logger.info('Test message')

            # File should exist
            self.assertTrue(log_file.exists())

            # Close handlers before cleanup
            self._close_logger_handlers(logger)

    def test_file_logger_has_multiple_handlers(self):
        """Test that file logger has both console and file handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            logger = setup_file_logger('test_file_logger_handlers', log_file)

            # Should have at least 2 handlers (console + file)
            self.assertGreaterEqual(len(logger.handlers), 2)

            # Close handlers before cleanup
            self._close_logger_handlers(logger)

    def test_file_logger_default_path(self):
        """Test file logger with default path."""
        logger = setup_file_logger('test_file_logger_default')

        self.assertIsInstance(logger, logging.Logger)


class TestGetLogger(unittest.TestCase):
    """Test get_logger function."""

    def test_get_logger_basic(self):
        """Test basic get_logger."""
        logger = get_logger('test_get_logger')

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'test_get_logger')

    def test_get_logger_creates_handlers(self):
        """Test that get_logger creates handlers if they don't exist."""
        logger = get_logger('test_get_logger_new')

        self.assertGreater(len(logger.handlers), 0)

    def test_get_logger_reuses_existing(self):
        """Test that get_logger reuses existing logger."""
        logger1 = get_logger('test_get_logger_reuse')
        logger2 = get_logger('test_get_logger_reuse')

        self.assertIs(logger1, logger2)

    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns already configured logger."""
        # First configure the logger
        setup_logger('test_get_logger_configured', logging.DEBUG)

        # Then get it
        logger = get_logger('test_get_logger_configured')

        self.assertEqual(logger.level, logging.DEBUG)


class TestLoggerFunctionality(unittest.TestCase):
    """Test logger functionality."""

    def _close_logger_handlers(self, logger):
        """Close all handlers for a logger to prevent file locks on Windows."""
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)

    def test_logger_can_log_messages(self):
        """Test that logger can log messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            logger = setup_file_logger('test_logger_func', log_file)

            logger.info('Test info message')
            logger.warning('Test warning message')
            logger.error('Test error message')

            # Close handlers to flush and release file
            self._close_logger_handlers(logger)

            # Read log file
            content = log_file.read_text()

            self.assertIn('Test info message', content)
            self.assertIn('Test warning message', content)
            self.assertIn('Test error message', content)

    def test_logger_respects_level(self):
        """Test that logger respects log level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            logger = setup_file_logger('test_logger_level', log_file, logging.WARNING)

            logger.debug('Debug message')
            logger.info('Info message')
            logger.warning('Warning message')
            logger.error('Error message')

            # Close handlers to flush and release file
            self._close_logger_handlers(logger)

            # Read log file
            content = log_file.read_text()

            # Should not contain debug or info
            self.assertNotIn('Debug message', content)
            self.assertNotIn('Info message', content)

            # Should contain warning and error
            self.assertIn('Warning message', content)
            self.assertIn('Error message', content)

    def test_logger_format(self):
        """Test that logger uses correct format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'test.log'
            logger = setup_file_logger('test_logger_format', log_file)

            logger.info('Test message')

            # Close handlers to flush and release file
            self._close_logger_handlers(logger)

            # Read log file
            content = log_file.read_text()

            # Should contain logger name and level
            self.assertIn('test_logger_format', content)
            self.assertIn('INFO', content)
            self.assertIn('Test message', content)


class TestAppLogger(unittest.TestCase):
    """Test the default app logger."""

    def test_app_logger_exists(self):
        """Test that app_logger is created."""
        from logger import app_logger

        self.assertIsInstance(app_logger, logging.Logger)

    def test_app_logger_name(self):
        """Test app logger has correct name."""
        from logger import app_logger

        self.assertEqual(app_logger.name, 'codecadet')


if __name__ == '__main__':
    unittest.main()
