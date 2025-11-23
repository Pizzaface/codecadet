"""Theme management for the application.

This module provides a centralized theme system following the Single Responsibility
Principle and DRY (Don't Repeat Yourself) principle.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ThemeColors:
    """Immutable color scheme for a theme."""
    bg: str
    panel: str
    surface: str
    text: str
    subtext: str
    accent: str
    sel_bg: str
    hover: str
    border: str


class Theme:
    """Base class for application themes."""

    def __init__(self, colors: ThemeColors):
        """Initialize theme with color scheme.

        Args:
            colors: ThemeColors instance defining the color palette
        """
        self.colors = colors

    def get_stylesheet(self) -> str:
        """Generate complete stylesheet for the theme.

        Returns:
            Complete QSS stylesheet string
        """
        c = self.colors

        return f"""
            QMainWindow {{
                background-color: {c.bg};
                color: {c.text};
            }}
            QWidget {{
                background-color: {c.bg};
                color: {c.text};
            }}
            QLabel {{
                color: {c.text};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {c.surface};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {c.hover};
            }}
            QPushButton:pressed {{
                background-color: {c.sel_bg};
            }}
            QComboBox {{
                background-color: {c.panel};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
            }}
            QComboBox:focus {{
                border: 2px solid {c.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                background-color: {c.surface};
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.panel};
                color: {c.text};
                selection-background-color: {c.accent};
                border: 1px solid {c.border};
            }}
            QCheckBox {{
                color: {c.text};
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                background-color: {c.panel};
                border: 1px solid {c.border};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {c.accent};
                border-color: {c.accent};
            }}
            QStatusBar {{
                background-color: {c.surface};
                color: {c.subtext};
                border-top: 1px solid {c.border};
            }}
            QMenuBar {{
                background-color: {c.bg};
                color: {c.text};
                border-bottom: 1px solid {c.border};
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 4px 8px;
            }}
            QMenuBar::item:selected {{
                background-color: {c.hover};
            }}
            QMenu {{
                background-color: {c.panel};
                color: {c.text};
                border: 1px solid {c.border};
            }}
            QMenu::item {{
                padding: 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {c.accent};
                color: #ffffff;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {c.border};
                margin: 2px 0;
            }}
            QSplitter::handle {{
                background-color: {c.border};
                width: 2px;
                height: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {c.accent};
            }}
        """


class ThemeManager:
    """Manages application themes following Single Responsibility Principle."""

    # Theme color schemes
    DARK_COLORS = ThemeColors(
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

    LIGHT_COLORS = ThemeColors(
        bg="#f5f6fb",
        panel="#ffffff",
        surface="#f0f2f7",
        text="#0e1116",
        subtext="#475569",
        accent="#4f46e5",
        sel_bg="#e5e7f9",
        hover="#eceffe",
        border="#d1d5db"
    )

    def __init__(self):
        """Initialize theme manager with available themes."""
        self._themes: Dict[str, Theme] = {
            "dark": Theme(self.DARK_COLORS),
            "light": Theme(self.LIGHT_COLORS)
        }
        self._current_theme = "dark"

    def get_theme(self, name: str) -> Theme:
        """Get theme by name.

        Args:
            name: Theme name ("dark" or "light")

        Returns:
            Theme instance

        Raises:
            KeyError: If theme name is not found
        """
        return self._themes[name]

    def get_stylesheet(self, name: str) -> str:
        """Get stylesheet for a theme.

        Args:
            name: Theme name ("dark" or "light")

        Returns:
            Complete QSS stylesheet string
        """
        return self.get_theme(name).get_stylesheet()

    def set_current_theme(self, name: str) -> None:
        """Set the current active theme.

        Args:
            name: Theme name

        Raises:
            KeyError: If theme name is not found
        """
        if name not in self._themes:
            raise KeyError(f"Theme '{name}' not found")
        self._current_theme = name

    def get_current_theme(self) -> str:
        """Get the current active theme name.

        Returns:
            Current theme name
        """
        return self._current_theme

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.

        Returns:
            List of theme names
        """
        return list(self._themes.keys())
