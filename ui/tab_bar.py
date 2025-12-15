"""Tab bar widget for managing multiple terminal sessions."""

from typing import Dict, Optional
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QTabBar, QPushButton, QHBoxLayout, QWidget,
    QMenu, QMessageBox, QInputDialog, QLineEdit, QToolButton
)
from PySide6.QtGui import QFont


class _CloseTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(False)
        self.setMovable(True)
        self.setExpanding(False)
        self.setUsesScrollButtons(True)
        self.setFont(QFont("Arial", 10))
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self._update_close_button(index)

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self._refresh_close_buttons()

    def _refresh_close_buttons(self):
        for i in range(self.count()):
            self._update_close_button(i)

    def _update_close_button(self, index: int):
        if index < 0 or index >= self.count():
            return
        btn = QToolButton(self)
        btn.setObjectName("terminalTabCloseButton")
        btn.setText("✕")
        btn.setAutoRaise(True)
        btn.setCursor(Qt.ArrowCursor)
        btn.clicked.connect(self._handle_close_clicked)
        self.setTabButton(index, QTabBar.RightSide, btn)

    def _handle_close_clicked(self):
        button = self.sender()
        if not button:
            return
        for i in range(self.count()):
            if self.tabButton(i, QTabBar.RightSide) is button:
                self.tabCloseRequested.emit(i)
                break


class TabBar(QWidget):
    """Custom tab bar for terminal sessions with new tab button."""
    
    # Signals
    tab_switched = Signal(str)  # tab_id
    tab_close_requested = Signal(str)  # tab_id
    tab_new_requested = Signal()
    tab_rename_requested = Signal(str, str)  # tab_id, new_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs: Dict[str, str] = {}  # {tab_id: tab_name}
        self.active_tab_id: Optional[str] = None
        
        self._setup_ui()
        self._apply_dark_theme()
    
    def _setup_ui(self):
        """Setup the tab bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab bar
        self.tab_bar = _CloseTabBar()
        
        # Connect signals
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tab_bar.customContextMenuRequested.connect(self._on_context_menu_requested)
        
        layout.addWidget(self.tab_bar, 1)
        
        # New tab button
        self.new_tab_btn = QPushButton(" + ")
        self.new_tab_btn.setFixedSize(30, 24)
        self.new_tab_btn.setToolTip("New Tab (runs selected agent)")
        self.new_tab_btn.clicked.connect(self.tab_new_requested.emit)
        
        layout.addWidget(self.new_tab_btn)
    
    def _apply_dark_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            TabBar {
                background-color: #0d1117;
                border-bottom: 1px solid #30363d;
                padding: 0px;
            }
            QTabBar {
                background-color: transparent;
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                background-color: #161b22;
                color: #8b949e;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 8px 16px;
                padding-right: 28px;
                margin-right: 1px;
                min-width: 100px;
                font-size: 12px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #0d1117;
                color: #e6edf3;
                border-bottom: 2px solid #58a6ff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #21262d;
                color: #c9d1d9;
            }
            QTabBar::tab:first {
                margin-left: 8px;
            }
            #terminalTabCloseButton {
                background-color: transparent;
                color: #6e7681;
                border: none;
                border-radius: 4px;
                padding: 0;
                margin: 2px;
                min-width: 18px;
                min-height: 18px;
                max-width: 18px;
                max-height: 18px;
                font-size: 11px;
                font-weight: normal;
            }
            #terminalTabCloseButton:hover {
                background-color: #f85149;
                color: #ffffff;
            }
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                padding: 4px 10px;
                margin: 4px 8px 4px 4px;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
                color: #e6edf3;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
        """)
    
    def add_tab(self, tab_id: str, tab_name: str, make_active: bool = True):
        """Add a new tab."""
        if tab_id in self.tabs:
            return
        
        self.tabs[tab_id] = tab_name
        index = self.tab_bar.addTab(tab_name)
        
        # Store tab_id as data for lookup
        self.tab_bar.setTabData(index, tab_id)
        
        if make_active or len(self.tabs) == 1:
            self.tab_bar.setCurrentIndex(index)
            self.active_tab_id = tab_id
    
    def remove_tab(self, tab_id: str):
        """Remove a tab."""
        if tab_id not in self.tabs:
            return
        
        # Find the tab index
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == tab_id:
                self.tab_bar.removeTab(i)
                break
        
        del self.tabs[tab_id]
        
        # If the active tab was removed, activate another
        if self.active_tab_id == tab_id:
            if self.tabs:
                # Activate the first remaining tab
                first_tab_id = next(iter(self.tabs))
                for i in range(self.tab_bar.count()):
                    if self.tab_bar.tabData(i) == first_tab_id:
                        self.tab_bar.setCurrentIndex(i)
                        self.active_tab_id = first_tab_id
                        break
            else:
                self.active_tab_id = None
    
    def update_tab_name(self, tab_id: str, new_name: str):
        """Update the display name of a tab."""
        if tab_id not in self.tabs:
            return
        
        self.tabs[tab_id] = new_name
        
        # Update the tab bar display
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == tab_id:
                self.tab_bar.setTabText(i, new_name)
                break
    
    def set_active_tab(self, tab_id: str):
        """Set the active tab by ID."""
        if tab_id not in self.tabs:
            return
        
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabData(i) == tab_id:
                self.tab_bar.setCurrentIndex(i)
                self.active_tab_id = tab_id
                break
    
    def clear_all_tabs(self):
        """Remove all tabs."""
        # QTabBar doesn't have a clear() method, so remove tabs one by one
        while self.tab_bar.count() > 0:
            self.tab_bar.removeTab(0)
        self.tabs.clear()
        self.active_tab_id = None
    
    def _on_tab_changed(self, index: int):
        """Handle tab selection change."""
        if index >= 0:
            tab_id = self.tab_bar.tabData(index)
            if tab_id and tab_id != self.active_tab_id:
                self.active_tab_id = tab_id
                self.tab_switched.emit(tab_id)
    
    def _on_tab_close_requested(self, index: int):
        """Handle tab close request."""
        tab_id = self.tab_bar.tabData(index)
        if tab_id:
            self.tab_close_requested.emit(tab_id)
    
    def _on_context_menu_requested(self, pos):
        """Handle context menu request on tab bar."""
        # Get the tab at the clicked position
        tab_index = self.tab_bar.tabAt(pos)
        
        if tab_index >= 0:
            tab_id = self.tab_bar.tabData(tab_index)
            if tab_id:
                self._show_context_menu(tab_id, tab_index, pos)
    
    def _show_context_menu(self, tab_id: str, index: int, pos):
        """Show context menu for a tab."""
        menu = QMenu(self)
        
        # Rename action
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self._rename_tab(tab_id))
        
        menu.addSeparator()
        
        # Close action
        close_action = menu.addAction("Close")
        close_action.triggered.connect(lambda: self.tab_close_requested.emit(tab_id))
        
        # Show menu at the requested position (already in widget coordinates)
        menu.exec_(self.tab_bar.mapToGlobal(pos))
    
    def _rename_tab(self, tab_id: str):
        """Prompt user to rename a tab."""
        if tab_id not in self.tabs:
            return
        
        current_name = self.tabs[tab_id]
        new_name, ok = QInputDialog.getText(
            self, 
            "Rename Tab", 
            "Enter new tab name:",
            QLineEdit.EchoMode.Normal,
            current_name
        )
        
        if ok and new_name.strip():
            self.tab_rename_requested.emit(tab_id, new_name.strip())
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        # Ctrl+T for new tab
        if event.key() == Qt.Key_T and event.modifiers() == Qt.ControlModifier:
            self.tab_new_requested.emit()
        # Ctrl+W for closing current tab
        elif event.key() == Qt.Key_W and event.modifiers() == Qt.ControlModifier:
            if self.active_tab_id:
                self.tab_close_requested.emit(self.active_tab_id)
        else:
            super().keyPressEvent(event)
