"""PTY-based terminal widget for Mac compatibility."""

import os
import pty
import select
import subprocess
import fcntl
import struct
import termios
import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QTextCursor, QKeyEvent, QTextCharFormat, QColor, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import QTextEdit


class ANSIColorParser:
    """Parser for ANSI color codes and terminal formatting."""
    
    # Standard ANSI color codes
    COLORS = {
        30: QColor(0, 0, 0),        # Black
        31: QColor(205, 49, 49),    # Red
        32: QColor(13, 188, 121),   # Green
        33: QColor(229, 229, 16),   # Yellow
        34: QColor(36, 114, 200),   # Blue
        35: QColor(188, 63, 188),   # Magenta
        36: QColor(17, 168, 205),   # Cyan
        37: QColor(229, 229, 229),  # White
        # Bright colors
        90: QColor(102, 102, 102),  # Bright Black (Gray)
        91: QColor(241, 76, 76),    # Bright Red
        92: QColor(35, 209, 139),   # Bright Green
        93: QColor(245, 245, 67),   # Bright Yellow
        94: QColor(59, 142, 234),   # Bright Blue
        95: QColor(214, 112, 214),  # Bright Magenta
        96: QColor(41, 184, 219),   # Bright Cyan
        97: QColor(255, 255, 255),  # Bright White
    }
    
    # Background colors (add 10 to foreground codes)
    BG_COLORS = {k + 10: v for k, v in COLORS.items() if k < 90}
    BG_COLORS.update({k + 10: v for k, v in COLORS.items() if k >= 90})
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset formatting to default."""
        self.fg_color = QColor(255, 255, 255)  # Default white
        self.bg_color = QColor(0, 0, 0)        # Default black
        self.bold = False
        self.italic = False
        self.underline = False
    
    def parse_escape_sequence(self, match):
        """Parse ANSI escape sequence and return QTextCharFormat."""
        codes = match.group(1)
        if not codes:
            codes = "0"
        
        format_obj = QTextCharFormat()
        
        # Parse codes
        code_parts = codes.split(';')
        i = 0
        while i < len(code_parts):
            try:
                num = int(code_parts[i]) if code_parts[i] else 0
                
                if num == 0:  # Reset
                    self.reset()
                elif num == 1:  # Bold
                    self.bold = True
                elif num == 3:  # Italic
                    self.italic = True
                elif num == 4:  # Underline
                    self.underline = True
                elif num == 22:  # Normal intensity (not bold)
                    self.bold = False
                elif num == 23:  # Not italic
                    self.italic = False
                elif num == 24:  # Not underlined
                    self.underline = False
                elif 30 <= num <= 37 or 90 <= num <= 97:  # Standard foreground colors
                    self.fg_color = self.COLORS.get(num, QColor(255, 255, 255))
                elif 40 <= num <= 47 or 100 <= num <= 107:  # Standard background colors
                    self.bg_color = self.BG_COLORS.get(num, QColor(0, 0, 0))
                elif num == 38:  # Extended foreground color
                    if i + 1 < len(code_parts):
                        color_type = int(code_parts[i + 1])
                        if color_type == 2 and i + 4 < len(code_parts):  # 24-bit RGB
                            r = int(code_parts[i + 2])
                            g = int(code_parts[i + 3])
                            b = int(code_parts[i + 4])
                            self.fg_color = QColor(r, g, b)
                            i += 4  # Skip the RGB values
                        elif color_type == 5 and i + 2 < len(code_parts):  # 256-color palette
                            color_index = int(code_parts[i + 2])
                            self.fg_color = self._get_256_color(color_index)
                            i += 2  # Skip the color index
                        else:
                            i += 1
                    else:
                        i += 1
                elif num == 48:  # Extended background color
                    if i + 1 < len(code_parts):
                        color_type = int(code_parts[i + 1])
                        if color_type == 2 and i + 4 < len(code_parts):  # 24-bit RGB
                            r = int(code_parts[i + 2])
                            g = int(code_parts[i + 3])
                            b = int(code_parts[i + 4])
                            self.bg_color = QColor(r, g, b)
                            i += 4  # Skip the RGB values
                        elif color_type == 5 and i + 2 < len(code_parts):  # 256-color palette
                            color_index = int(code_parts[i + 2])
                            self.bg_color = self._get_256_color(color_index)
                            i += 2  # Skip the color index
                        else:
                            i += 1
                    else:
                        i += 1
                elif num == 39:  # Default foreground
                    self.fg_color = QColor(255, 255, 255)
                elif num == 49:  # Default background
                    self.bg_color = QColor(0, 0, 0)
                    
            except (ValueError, IndexError):
                pass
            
            i += 1
        
        # Apply formatting
        format_obj.setForeground(self.fg_color)
        format_obj.setBackground(self.bg_color)
        if self.bold:
            format_obj.setFontWeight(QFont.Weight.Bold)
        if self.italic:
            format_obj.setFontItalic(True)
        if self.underline:
            format_obj.setFontUnderline(True)
            
        return format_obj
    
    def _get_256_color(self, index):
        """Convert 256-color palette index to QColor."""
        if index < 16:
            # Standard colors
            return self.COLORS.get(30 + (index % 8), QColor(255, 255, 255))
        elif index < 232:
            # 216-color cube
            index -= 16
            r = (index // 36) * 51
            g = ((index % 36) // 6) * 51
            b = (index % 6) * 51
            return QColor(r, g, b)
        else:
            # Grayscale
            gray = (index - 232) * 10 + 8
            return QColor(gray, gray, gray)
    
    def get_current_format(self):
        """Get current formatting as QTextCharFormat."""
        format_obj = QTextCharFormat()
        format_obj.setForeground(self.fg_color)
        format_obj.setBackground(self.bg_color)
        if self.bold:
            format_obj.setFontWeight(QFont.Weight.Bold)
        if self.italic:
            format_obj.setFontItalic(True)
        if self.underline:
            format_obj.setFontUnderline(True)
        return format_obj


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


class PTYTerminalWidget(QTextEdit):
    """A simple terminal emulator widget using PTY."""
    
    bell_triggered = Signal()  # Signal when terminal bell is triggered
    
    def __init__(self, parent, command, cwd):
        super().__init__(parent)
        
        # Initialize ANSI color parser
        self.color_parser = ANSIColorParser()
        
        # Buffer for handling partial ANSI sequences
        self.data_buffer = ""
        
        # Setup appearance - white text on black for better visibility
        self.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #ffffff;
                border: none;
                padding: 5px;
            }
        """)
        
        # Set monospace font with Unicode box-drawing support
        # Try fonts in order of preference for proper Unicode support
        font_families = ["SF Mono", "Monaco", "Menlo", "Consolas", "DejaVu Sans Mono"]
        font = None
        
        for family in font_families:
            test_font = QFont(family, 11)
            if QFontDatabase.families().__contains__(family):
                font = test_font
                break
        
        if font is None:
            font = QFont("monospace", 11)
        
        font.setFixedPitch(True)
        font.setStyleHint(QFont.StyleHint.Monospace)
        # Ensure proper character spacing for Unicode box drawing
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0)
        font.setKerning(False)
        self.setFont(font)
        
        # Terminal settings
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
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
                # Set environment for proper terminal and character support
                os.environ['TERM'] = 'xterm-256color'  # Enable color support
                os.environ['COLUMNS'] = '80'
                os.environ['LINES'] = '24'
                os.environ['LANG'] = 'en_US.UTF-8'  # Ensure UTF-8
                os.environ['LC_ALL'] = 'en_US.UTF-8'  # Force UTF-8 for all categories
                os.environ['LC_CTYPE'] = 'en_US.UTF-8'  # Character classification
                os.environ['COLORTERM'] = 'truecolor'  # Enable true color support
                # Force colored output from common tools
                os.environ['CLICOLOR'] = '1'
                os.environ['CLICOLOR_FORCE'] = '1'
                # Ensure proper Unicode handling
                os.environ['PYTHONIOENCODING'] = 'utf-8'
                
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
        """Handle data received from PTY with ANSI color support."""
        try:
            # More robust UTF-8 decoding with better error handling
            text = data.decode('utf-8', errors='replace')
            
            # Handle common problematic sequences
            # Replace replacement character with space to avoid display issues
            text = text.replace('\ufffd', ' ')
            
            # Add to buffer to handle partial ANSI sequences
            self.data_buffer += text
            
            # Process complete sequences from the buffer
            self._process_buffered_data()
            
        except Exception as e:
            # Fallback - just display raw text with better error handling
            try:
                fallback_text = data.decode('utf-8', errors='replace').replace('\ufffd', ' ')
            except:
                fallback_text = str(data, errors='ignore')
            
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(fallback_text)
            self.setTextCursor(cursor)
    
    def _process_buffered_data(self):
        """Process buffered data, handling partial ANSI sequences."""
        # Check for complete ANSI escape sequences and special commands
        text = self.data_buffer
        
        # Handle clear screen
        if '\x1b[2J' in text or '\x1b[3J' in text:
            self.clear()
            self.color_parser.reset()
            text = re.sub(r'\x1b\[[23]J', '', text)
        
        # Handle cursor home
        if '\x1b[H' in text:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.setTextCursor(cursor)
            text = text.replace('\x1b[H', '')
        
        # Remove non-color control sequences
        text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)  # Cursor visibility
        text = re.sub(r'\x1b\[[0-9]+;[0-9]+H', '', text)  # Cursor positioning
        text = re.sub(r'\x1b\[[0-9]*[GKJ]', '', text)  # Column/line operations
        text = re.sub(r'\x1b\[K', '', text)  # Clear to end of line
        
        # Handle carriage returns more robustly
        # Many CLIs use '\r' to redraw the same line (spinners/progress).
        # Always treat bare '\r' as "return to start of line and overwrite",
        # regardless of whether a '\n' also appears in the same chunk.
        if '\r\n' in text:
            # Normalize CRLF to LF first
            text = text.replace('\r\n', '\n')
        if '\r' in text:
            # Clear the current line in the widget before applying updated content
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            # For each logical line in this chunk, keep only the portion after the last CR
            # This collapses multiple CR-updates in one chunk to the final frame, preventing
            # stray carriage returns from creating visual newlines.
            parts = text.split('\n')
            parts = [p.split('\r')[-1] for p in parts]
            text = '\n'.join(parts)
        
        # Process ANSI color sequences
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        pattern = r'\x1b\[([0-9;]*?)m'
        last_pos = 0
        
        for match in re.finditer(pattern, text):
            # Insert text before this escape sequence
            before_text = text[last_pos:match.start()]
            if before_text:
                char_format = self.color_parser.get_current_format()
                cursor.setCharFormat(char_format)
                cursor.insertText(before_text)
            
            # Process the escape sequence
            codes = match.group(1)
            class DummyMatch:
                def __init__(self, codes):
                    self._codes = codes
                def group(self, n):
                    return self._codes
            
            self.color_parser.parse_escape_sequence(DummyMatch(codes))
            last_pos = match.end()
        
        # Handle remaining text after last escape sequence
        remaining_text = text[last_pos:]
        
        # Check if we have an incomplete ANSI sequence at the end
        incomplete_match = re.search(r'\x1b\[[0-9;]*$', remaining_text)
        if incomplete_match:
            # We have an incomplete ANSI sequence - keep it in buffer
            complete_text = remaining_text[:incomplete_match.start()]
            self.data_buffer = remaining_text[incomplete_match.start():]
            
            if complete_text:
                char_format = self.color_parser.get_current_format()
                cursor.setCharFormat(char_format)
                cursor.insertText(complete_text)
        else:
            # No incomplete sequence - process all remaining text and clear buffer
            if remaining_text:
                char_format = self.color_parser.get_current_format()
                cursor.setCharFormat(char_format)
                cursor.insertText(remaining_text)
            self.data_buffer = ""
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Send key presses to PTY."""
        if not self.master_fd:
            return
        
        key = event.key()
        modifiers = event.modifiers()
        text = ''
        
        # Map keys to terminal sequences
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            text = '\r'
        elif key == Qt.Key.Key_Backspace:
            text = '\x08'  # Use ASCII backspace instead of DEL
        elif key == Qt.Key.Key_Delete:
            text = '\x7f'  # DEL character for forward delete
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
        elif key == Qt.Key.Key_Home:
            text = '\x1b[H'
        elif key == Qt.Key.Key_End:
            text = '\x1b[F'
        elif key == Qt.Key.Key_PageUp:
            text = '\x1b[5~'
        elif key == Qt.Key.Key_PageDown:
            text = '\x1b[6~'
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
        
        # Send to PTY with proper encoding
        if text:
            try:
                # Ensure text is properly encoded as UTF-8 bytes
                encoded_text = text.encode('utf-8', errors='replace')
                os.write(self.master_fd, encoded_text)
            except OSError:
                pass
            except UnicodeEncodeError:
                # Fallback for problematic characters
                try:
                    safe_text = text.encode('ascii', errors='ignore').decode('ascii')
                    os.write(self.master_fd, safe_text.encode('utf-8'))
                except:
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

