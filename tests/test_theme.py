"""Tests for the theme management module."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from ui.theme import ThemeManager, Theme, ThemeColors


class TestThemeColors(unittest.TestCase):
    """Test ThemeColors dataclass."""

    def test_theme_colors_immutable(self):
        """Test that ThemeColors is immutable (frozen)."""
        colors = ThemeColors(
            bg="#000000",
            panel="#111111",
            surface="#222222",
            text="#ffffff",
            subtext="#cccccc",
            accent="#ff0000",
            sel_bg="#333333",
            hover="#444444",
            border="#555555"
        )

        # Should not be able to modify frozen dataclass
        with self.assertRaises(AttributeError):
            colors.bg = "#999999"

    def test_theme_colors_creation(self):
        """Test creating ThemeColors with all required fields."""
        colors = ThemeColors(
            bg="#0f1115",
            panel="#151823",
            surface="#1a1f2e",
            text="#e6e7ee",
            subtext="#9aa1b2",
            accent="#7c7fff",
            sel_bg="#26304a",
            hover="#20273a",
            border="#404757"
        )

        self.assertEqual(colors.bg, "#0f1115")
        self.assertEqual(colors.accent, "#7c7fff")


class TestTheme(unittest.TestCase):
    """Test Theme class."""

    def setUp(self):
        """Set up test theme."""
        self.colors = ThemeColors(
            bg="#000000",
            panel="#111111",
            surface="#222222",
            text="#ffffff",
            subtext="#cccccc",
            accent="#ff0000",
            sel_bg="#333333",
            hover="#444444",
            border="#555555"
        )
        self.theme = Theme(self.colors)

    def test_get_stylesheet(self):
        """Test that stylesheet is generated."""
        stylesheet = self.theme.get_stylesheet()

        self.assertIsInstance(stylesheet, str)
        self.assertGreater(len(stylesheet), 100)

    def test_stylesheet_contains_widget_styles(self):
        """Test that stylesheet contains expected widget styles."""
        stylesheet = self.theme.get_stylesheet()

        # Should contain styles for main widgets
        self.assertIn("QMainWindow", stylesheet)
        self.assertIn("QPushButton", stylesheet)
        self.assertIn("QComboBox", stylesheet)
        self.assertIn("QMenuBar", stylesheet)

    def test_stylesheet_uses_theme_colors(self):
        """Test that stylesheet uses the theme colors."""
        stylesheet = self.theme.get_stylesheet()

        # Should use colors from ThemeColors
        self.assertIn(self.colors.bg, stylesheet)
        self.assertIn(self.colors.accent, stylesheet)
        self.assertIn(self.colors.border, stylesheet)


class TestThemeManager(unittest.TestCase):
    """Test ThemeManager class."""

    def setUp(self):
        """Set up test theme manager."""
        self.manager = ThemeManager()

    def test_available_themes(self):
        """Test that default themes are available."""
        themes = self.manager.get_available_themes()

        self.assertIn("dark", themes)
        self.assertIn("light", themes)
        self.assertEqual(len(themes), 2)

    def test_get_theme(self):
        """Test getting a theme by name."""
        dark_theme = self.manager.get_theme("dark")
        light_theme = self.manager.get_theme("light")

        self.assertIsInstance(dark_theme, Theme)
        self.assertIsInstance(light_theme, Theme)

    def test_get_theme_invalid(self):
        """Test getting an invalid theme raises KeyError."""
        with self.assertRaises(KeyError):
            self.manager.get_theme("invalid_theme")

    def test_get_stylesheet(self):
        """Test getting stylesheet by theme name."""
        dark_css = self.manager.get_stylesheet("dark")
        light_css = self.manager.get_stylesheet("light")

        self.assertIsInstance(dark_css, str)
        self.assertIsInstance(light_css, str)
        self.assertGreater(len(dark_css), 1000)
        self.assertGreater(len(light_css), 1000)

    def test_dark_theme_colors(self):
        """Test that dark theme has expected colors."""
        dark_css = self.manager.get_stylesheet("dark")

        # Dark theme should have dark background
        self.assertIn("#0f1115", dark_css)  # bg
        self.assertIn("#7c7fff", dark_css)  # accent

    def test_light_theme_colors(self):
        """Test that light theme has expected colors."""
        light_css = self.manager.get_stylesheet("light")

        # Light theme should have light background
        self.assertIn("#f5f6fb", light_css)  # bg
        self.assertIn("#4f46e5", light_css)  # accent

    def test_set_current_theme(self):
        """Test setting the current theme."""
        self.manager.set_current_theme("light")
        self.assertEqual(self.manager.get_current_theme(), "light")

        self.manager.set_current_theme("dark")
        self.assertEqual(self.manager.get_current_theme(), "dark")

    def test_set_current_theme_invalid(self):
        """Test setting an invalid theme raises KeyError."""
        with self.assertRaises(KeyError):
            self.manager.set_current_theme("invalid_theme")

    def test_default_theme(self):
        """Test that default theme is dark."""
        self.assertEqual(self.manager.get_current_theme(), "dark")


if __name__ == '__main__':
    unittest.main()
