"""Clipboard utilities for PySide6 widgets."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QMenu


def setup_entry_clipboard(entry_widget):
    """Set up clipboard operations for a PySide6 widget."""
    if isinstance(entry_widget, QComboBox):
        # For QComboBox, work with its line edit
        line_edit = entry_widget.lineEdit()
        if line_edit:
            setup_line_edit_clipboard(line_edit)
    elif isinstance(entry_widget, QLineEdit):
        setup_line_edit_clipboard(entry_widget)


def setup_line_edit_clipboard(line_edit):
    """Set up clipboard operations for a QLineEdit widget."""
    # Standard clipboard shortcuts (Qt already handles these by default, but we'll ensure they work)
    # Qt widgets have built-in clipboard support, but we'll add context menu
    setup_entry_context_menu(line_edit)


def setup_entry_context_menu(entry):
    """Add a right-click context menu with clipboard operations."""

    def show_context_menu(position):
        """Show the context menu at the cursor position."""
        context_menu = QMenu(entry)

        # Cut action
        cut_action = QAction("Cut", context_menu)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(lambda: cut_from_widget(entry))
        cut_action.setEnabled(entry.hasSelectedText())
        context_menu.addAction(cut_action)

        # Copy action
        copy_action = QAction("Copy", context_menu)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(lambda: copy_from_widget(entry))
        copy_action.setEnabled(entry.hasSelectedText())
        context_menu.addAction(copy_action)

        # Paste action
        paste_action = QAction("Paste", context_menu)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(lambda: paste_to_widget(entry))
        clipboard = QApplication.clipboard()
        paste_action.setEnabled(clipboard.mimeData().hasText())
        context_menu.addAction(paste_action)

        context_menu.addSeparator()

        # Select All action
        select_all_action = QAction("Select All", context_menu)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(entry.selectAll)
        select_all_action.setEnabled(not entry.text().isEmpty())
        context_menu.addAction(select_all_action)

        # Show the context menu
        context_menu.exec(entry.mapToGlobal(position))

    # Connect the context menu to right-click
    entry.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    entry.customContextMenuRequested.connect(show_context_menu)


def copy_from_widget(widget):
    """Copy selected text from widget to clipboard."""
    if isinstance(widget, QLineEdit):
        if widget.hasSelectedText():
            clipboard = QApplication.clipboard()
            clipboard.setText(widget.selectedText())


def paste_to_widget(widget):
    """Paste clipboard content into widget at cursor or replace selection."""
    if isinstance(widget, QLineEdit):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            if widget.hasSelectedText():
                # Replace selection
                widget.insert(text)
            else:
                # Insert at cursor
                cursor_pos = widget.cursorPosition()
                current_text = widget.text()
                new_text = current_text[:cursor_pos] + text + current_text[cursor_pos:]
                widget.setText(new_text)
                widget.setCursorPosition(cursor_pos + len(text))


def cut_from_widget(widget):
    """Cut selected text from widget to clipboard."""
    if isinstance(widget, QLineEdit):
        if widget.hasSelectedText():
            copy_from_widget(widget)
            widget.del_()  # Delete selected text
