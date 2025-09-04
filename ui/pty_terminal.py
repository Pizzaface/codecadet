"""PTY-based terminal widget for Mac compatibility."""

import os
import pty
import select
import subprocess
import fcntl
import struct
import termios
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QTextCursor, QKeyEvent, QTextCharFormat, QColor, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import QPlainTextEdit


class PTYReader(QThread):
    """Background thread for reading PTY output."""
    data_received = Signal(bytes)
    
    def __init__(self, fd):
        super().__init__()
        self.fd = fd
        self.running = True
    
    def run(self):
        """Read from PTY in background."""
        while self.running:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.1)
                if r:
                    data = os.read(self.fd, 4096)
                    if data:
                        self.data_received.emit(data)
                    else:
                        break
            except OSError:
                break
    
    def stop(self):
        """Stop the reader thread."""
        self.running = False


class PTYTerminalWidget(QPlainTextEdit):
    """A simple terminal emulator widget using PTY."""
    
    def __init__(self, parent, command, cwd):
        super().__init__(parent)
        
        # Setup appearance - white text on black for better visibility
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #000000;
                color: #ffffff;
                border: none;
                padding: 5px;
            }
        """)
        
        # Set monospace font with Unicode box-drawing support
        # Use Menlo which has proper box-drawing characters on macOS
        font = QFont("Menlo", 11)
        font.setFixedPitch(True)
        font.setStyleHint(QFont.StyleHint.Monospace)
        # Critical: Set zero letter spacing for box characters to connect
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100)
        self.setFont(font)
        
        # Terminal settings
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setReadOnly(False)
        self.setCursorWidth(2)
        
        # PTY state
        self.master_fd = None
        self.process = None
        self.reader = None
        
        # Start PTY session
        self._start_pty_session(command, cwd)
        
    def _start_pty_session(self, command, cwd):
        """Start a PTY session with the given command."""
        try:
            # Create PTY
            pid, fd = pty.fork()
            
            if pid == 0:  # Child process
                # Set environment for better terminal compatibility
                os.environ['TERM'] = 'dumb'  # Simple terminal without fancy features
                os.environ['COLUMNS'] = '80'
                os.environ['LINES'] = '24'
                os.environ['LANG'] = 'en_US.UTF-8'  # Ensure UTF-8
                
                # Change to working directory
                os.chdir(cwd)
                
                # Execute shell command
                os.execv('/bin/zsh', ['/bin/zsh', '-c', command])
            
            else:  # Parent process
                self.master_fd = fd
                self.process_pid = pid
                
                # Make non-blocking
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
                
                # Start reader thread
                self.reader = PTYReader(self.master_fd)
                self.reader.data_received.connect(self._on_data_received)
                self.reader.start()
                
        except Exception as e:
            self.appendPlainText(f"Failed to start terminal: {e}")
    
    def _on_data_received(self, data):
        """Handle data received from PTY."""
        try:
            # Decode with UTF-8 to preserve Unicode characters
            text = data.decode('utf-8', errors='ignore')
            
            # Handle ANSI escape sequences
            import re
            
            # Check for clear screen sequence
            if '\x1b[2J' in text or '\x1b[3J' in text:
                # Clear the widget
                self.clear()
                # Remove the clear sequence from text
                text = re.sub(r'\x1b\[[23]J', '', text)
            
            # Handle cursor home
            if '\x1b[H' in text:
                # Move cursor to beginning
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.setTextCursor(cursor)
                text = text.replace('\x1b[H', '')
            
            # Remove ANSI escape sequences but be more selective
            # Remove color codes (we can't render them in QPlainTextEdit)
            text = re.sub(r'\x1b\[[0-9;]*m', '', text)  # Color/style codes
            text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)  # Cursor visibility
            text = re.sub(r'\x1b\[[0-9]+;[0-9]+H', '', text)  # Cursor positioning
            text = re.sub(r'\x1b\[[0-9]*[GKJ]', '', text)  # Column/line operations
            text = re.sub(r'\x1b\[K', '', text)  # Clear to end of line
            
            # Handle carriage returns
            if '\r\n' in text:
                text = text.replace('\r\n', '\n')
            elif '\r' in text and '\n' not in text:
                # Carriage return without newline - overwrite current line
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                text = text.replace('\r', '')
            
            # Append text if there's content
            if text:
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(text)
                self.setTextCursor(cursor)
                self.ensureCursorVisible()
            
        except Exception:
            pass
    
    def keyPressEvent(self, event: QKeyEvent):
        """Send key presses to PTY."""
        if not self.master_fd:
            return
        
        key = event.key()
        modifiers = event.modifiers()
        text = ''
        
        # Map keys to terminal sequences
        if key == Qt.Key.Key_Return:
            text = '\r'
        elif key == Qt.Key.Key_Backspace:
            text = '\x7f'
        elif key == Qt.Key.Key_Tab:
            text = '\t'
        elif key == Qt.Key.Key_Escape:
            text = '\x1b'
        elif key == Qt.Key.Key_Up:
            text = '\x1b[A'
        elif key == Qt.Key.Key_Down:
            text = '\x1b[B'
        elif key == Qt.Key.Key_Right:
            text = '\x1b[C'
        elif key == Qt.Key.Key_Left:
            text = '\x1b[D'
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:
                text = '\x03'
            elif key == Qt.Key.Key_D:
                text = '\x04'
            elif key == Qt.Key.Key_Z:
                text = '\x1a'
            elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                # Ctrl+A through Ctrl+Z
                text = chr(1 + key - Qt.Key.Key_A)
        else:
            # Normal character
            text = event.text()
        
        # Send to PTY
        if text:
            try:
                os.write(self.master_fd, text.encode('utf-8'))
            except OSError:
                pass
    
    def closeEvent(self, event):
        """Clean up when closing."""
        self._cleanup()
        super().closeEvent(event)
    
    def _cleanup(self):
        """Clean up PTY and reader thread."""
        if self.reader:
            self.reader.stop()
            self.reader.wait()
        
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        
        if hasattr(self, 'process_pid'):
            try:
                os.kill(self.process_pid, 15)  # SIGTERM
            except OSError:
                pass