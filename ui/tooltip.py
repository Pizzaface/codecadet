"""Tooltip utilities for enhanced user experience."""

from PySide6.QtCore import QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget


class ToolTip(QObject):
    """Enhanced tooltip widget with dark theme support."""

    def __init__(self, widget: QWidget, text: str, delay: int = 500, wraplength: int = 300):
        super().__init__(widget)
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.tooltip = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._show_tooltip)

        # Install event filter to capture mouse events
        self.widget.installEventFilter(self)
        self.widget.setMouseTracking(True)

    def eventFilter(self, obj, event):
        """Handle mouse events for tooltip display."""
        if obj == self.widget:
            if event.type() == event.Type.Enter:
                self._on_enter()
            elif event.type() == event.Type.Leave:
                self._on_leave()
            elif event.type() == event.Type.MouseMove and self.tooltip:
                self._update_position(event.globalPosition())
        return False

    def _on_enter(self):
        """Handle mouse enter event."""
        self.timer.start(self.delay)

    def _on_leave(self):
        """Handle mouse leave event."""
        self.timer.stop()
        self._hide_tooltip()

    def _update_position(self, global_pos):
        """Update tooltip position based on mouse movement."""
        if self.tooltip:
            x, y = self._get_tooltip_position(global_pos)
            self.tooltip.move(x, y)

    def _show_tooltip(self):
        """Show the tooltip."""
        if self.tooltip:
            return

        global_pos = self.widget.mapToGlobal(QPoint(0, 0))
        x, y = self._get_tooltip_position(global_pos)

        # Create tooltip window
        self.tooltip = QWidget(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.tooltip.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.tooltip.setWindowModality(Qt.WindowModality.NonModal)

        # Create label with wrapped text
        label = QLabel(self.text, self.tooltip)
        label.setFont(QFont("Arial", 9))
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                color: #e6e7ee;
                background-color: #2a2d37;
                padding: 8px;
                border: 1px solid #404757;
                border-radius: 4px;
            }
        """)

        # Set maximum width for word wrapping
        label.setMaximumWidth(self.wraplength)
        label.adjustSize()

        # Adjust tooltip size to fit label
        self.tooltip.resize(label.size())

        # Position and show tooltip
        self.tooltip.move(x, y)
        self.tooltip.show()
        self.tooltip.raise_()

    def _hide_tooltip(self):
        """Hide the tooltip."""
        if self.tooltip:
            self.tooltip.close()
            self.tooltip = None

    def _get_tooltip_position(self, global_pos):
        """Calculate optimal tooltip position."""
        x = int(global_pos.x()) + 15
        y = int(global_pos.y()) + 10

        # Get screen geometry
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        # Rough estimate of tooltip size
        tooltip_width = min(self.wraplength + 20, 320)
        tooltip_height = 50  # Rough estimate

        # Adjust position if tooltip would go off screen
        if x + tooltip_width > screen_geometry.right():
            x = screen_geometry.right() - tooltip_width - 10
        if y + tooltip_height > screen_geometry.bottom():
            y = y - tooltip_height - 30

        return x, y

    def update_text(self, new_text: str):
        """Update tooltip text."""
        self.text = new_text
        if self.tooltip:
            # If tooltip is currently shown, recreate it with new text
            self._hide_tooltip()
            self._show_tooltip()


class StatusTooltip(QObject):
    """Special tooltip for status messages that appear temporarily."""

    def __init__(self, widget: QWidget, duration: int = 3000):
        super().__init__(widget)
        self.widget = widget
        self.duration = duration
        self.tooltip = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._hide_message)

    def show_message(self, message: str, message_type: str = "info"):
        """Show a temporary status message."""
        self._hide_message()

        # Calculate position
        widget_pos = self.widget.mapToGlobal(QPoint(0, 0))
        x = widget_pos.x() + 10
        y = widget_pos.y() - 40

        # Create tooltip window
        self.tooltip = QWidget(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.tooltip.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.tooltip.setWindowModality(Qt.WindowModality.NonModal)

        # Choose colors based on message type
        colors = {
            "info": {"bg": "#2563eb", "text": "#ffffff"},
            "success": {"bg": "#16a34a", "text": "#ffffff"},
            "warning": {"bg": "#ea580c", "text": "#ffffff"},
            "error": {"bg": "#dc2626", "text": "#ffffff"}
        }

        color_scheme = colors.get(message_type, colors["info"])

        # Create label
        label = QLabel(message, self.tooltip)
        label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        label.setStyleSheet(f"""
            QLabel {{
                color: {color_scheme["text"]};
                background-color: {color_scheme["bg"]};
                padding: 6px 12px;
                border: 1px solid {color_scheme["bg"]};
                border-radius: 4px;
            }}
        """)
        label.adjustSize()

        # Adjust tooltip size to fit label
        self.tooltip.resize(label.size())

        # Position and show tooltip
        self.tooltip.move(x, y)
        self.tooltip.show()
        self.tooltip.raise_()

        # Auto-hide after duration
        self.timer.start(self.duration)

    def _hide_message(self):
        """Hide the status message."""
        if self.tooltip:
            self.tooltip.close()
            self.tooltip = None


def add_tooltip(widget: QWidget, text: str, delay: int = 500, wraplength: int = 300) -> ToolTip:
    """Convenience function to add a tooltip to a widget."""
    return ToolTip(widget, text, delay, wraplength)


def add_tooltip_to_button(button: QWidget, text: str, delay: int = 400) -> ToolTip:
    """Convenience function specifically for buttons with shorter delay."""
    return ToolTip(button, text, delay, wraplength=250)
