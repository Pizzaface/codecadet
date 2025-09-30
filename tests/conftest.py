"""Test configuration and fixtures for pytest."""

import sys
from unittest.mock import MagicMock

# Mock PySide6 modules to avoid GUI dependencies in headless test environment
def mock_pyside6():
    """Mock PySide6 modules for testing without GUI dependencies."""
    # Create mock modules
    pyside6_mock = MagicMock()
    qtwidgets_mock = MagicMock()
    qtcore_mock = MagicMock()
    qtgui_mock = MagicMock()
    
    # Mock QWidget class
    class MockQWidget:
        def __init__(self, *args, **kwargs):
            pass
    
    # Set up the mock hierarchy
    qtwidgets_mock.QWidget = MockQWidget
    pyside6_mock.QtWidgets = qtwidgets_mock
    pyside6_mock.QtCore = qtcore_mock
    pyside6_mock.QtGui = qtgui_mock
    
    # Install mocks in sys.modules
    sys.modules['PySide6'] = pyside6_mock
    sys.modules['PySide6.QtWidgets'] = qtwidgets_mock
    sys.modules['PySide6.QtCore'] = qtcore_mock
    sys.modules['PySide6.QtGui'] = qtgui_mock

# Mock PySide6 before any imports
mock_pyside6()
