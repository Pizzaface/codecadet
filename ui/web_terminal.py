"""Web-based terminal widget using xterm.js for better character handling."""

import os
import pty
import select
import json
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QObject, Slot, Signal, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtMultimedia import QSoundEffect

INACTIVITY_TIMER = 3


class TerminalBridge(QObject):
    """Bridge between the web terminal and PTY."""
    
    data_received = Signal(str)
    inactivity_detected = Signal()  # Signal when no output for 10 seconds
    
    def __init__(self):
        super().__init__()
        self.master_fd = None
        self.process_pid = None
        self.reader_thread = None
        self.running = False
        self.last_output_time = None
        self.inactivity_timer = QTimer()
        self.inactivity_timer.timeout.connect(self._check_inactivity)
        self.inactivity_timer.start(1000)  # Check every second
        self.inactivity_triggered = False
        
    def start_pty(self, command, cwd):
        """Start PTY process."""
        try:
            pid, fd = pty.fork()
            
            if pid == 0:  # Child process
                # Close parent's stdout/stderr to prevent interference
                import sys
                sys.stdout.flush()
                sys.stderr.flush()
                
                # Set environment for proper terminal and character support
                os.environ['TERM'] = 'xterm-256color'
                os.environ['COLUMNS'] = '120'  # Wider default
                os.environ['LINES'] = '30'     # Taller default
                os.environ['LANG'] = 'en_US.UTF-8'
                os.environ['LC_ALL'] = 'en_US.UTF-8'
                os.environ['LC_CTYPE'] = 'en_US.UTF-8'
                os.environ['COLORTERM'] = 'truecolor'
                os.environ['CLICOLOR'] = '1'
                os.environ['CLICOLOR_FORCE'] = '1'
                os.environ['PYTHONIOENCODING'] = 'utf-8'
                
                # Change to working directory
                os.chdir(cwd)
                
                # Execute shell command
                os.execv('/bin/zsh', ['/bin/zsh', '-c', command])
            
            else:  # Parent process
                self.master_fd = fd
                self.process_pid = pid
                self.running = True
                
                # Start reader thread
                self.reader_thread = threading.Thread(target=self._read_pty)
                self.reader_thread.daemon = True
                self.reader_thread.start()
                
                return True
                
        except Exception as e:
            pass  # Failed to start PTY
            return False
    
    def _read_pty(self):
        """Read from PTY in background thread."""
        while self.running and self.master_fd:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if r:
                    data = os.read(self.master_fd, 4096)
                    if data:
                        # Update last output time and reset inactivity flag
                        self.last_output_time = time.time()
                        self.inactivity_triggered = False
                        # Decode and emit data
                        text = data.decode('utf-8', errors='replace')
                        self.data_received.emit(text)
                    else:
                        break
            except OSError:
                break
    
    def _check_inactivity(self):
        """Check if there's been no output for 10 seconds."""
        if self.last_output_time and not self.inactivity_triggered:
            time_since_output = time.time() - self.last_output_time
            if time_since_output >= INACTIVITY_TIMER:  # 10 seconds of inactivity
                self.inactivity_triggered = True
                self.inactivity_detected.emit()
    
    @Slot(str)
    def write_to_pty(self, data):
        """Write data to PTY."""
        if self.master_fd and data:
            try:
                os.write(self.master_fd, data.encode('utf-8'))
            except OSError:
                pass
    
    @Slot(int, int)
    def resize_pty(self, cols, rows):
        """Resize the PTY."""
        if self.master_fd:
            try:
                import fcntl
                import struct
                import termios
                # Set the terminal size
                s = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, s)
            except OSError:
                pass
    
    def cleanup(self):
        """Clean up PTY resources."""
        self.running = False
        self.inactivity_timer.stop()
        
        if self.reader_thread:
            self.reader_thread.join(timeout=1.0)
        
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        
        if self.process_pid:
            try:
                os.kill(self.process_pid, 15)  # SIGTERM
            except OSError:
                pass


class WebTerminalWidget(QWidget):
    """Web-based terminal widget using xterm.js."""
    
    def __init__(self, parent, command, cwd):
        super().__init__(parent)
        
        self.bridge = TerminalBridge()
        self.bridge.data_received.connect(self._on_data_received)
        self.bridge.inactivity_detected.connect(self._on_inactivity_detected)
        
        # Setup sound effect for inactivity notification
        self.sound_effect = QSoundEffect()
        self._load_notification_sound()
        
        self._setup_ui()
        self._start_terminal(command, cwd)
    
    def _setup_ui(self):
        """Setup the web view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view
        self.web_view = QWebEngineView()
        
        # Enable JavaScript
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # Set up web channel for communication
        self.channel = QWebChannel()
        self.channel.registerObject("qtBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        
        # Create terminal HTML page
        html_content = self._create_terminal_html()
        self.web_view.setHtml(html_content)
        
        layout.addWidget(self.web_view)
    
    def _create_terminal_html(self):
        """Create HTML content with xterm.js terminal."""
        return Path(__file__).parent.parent.joinpath("assets", "web-terminal.html").read_text()
    
    def _start_terminal(self, command, cwd):
        """Start the terminal session."""
        # Wait for web page to load
        QTimer.singleShot(500, lambda: self._connect_bridge_and_start(command, cwd))
    
    def _connect_bridge_and_start(self, command, cwd):
        """Connect the bridge and start PTY."""
        # Start PTY
        if self.bridge.start_pty(command, cwd):
            self.web_view.page().runJavaScript("console.log('PTY started successfully')")
        else:
            self.web_view.page().runJavaScript("window.writeToTerminal('Failed to start terminal session\\r\\n')")
    
    def _on_data_received(self, data):
        """Handle data received from PTY."""
        # Escape data for JavaScript and send to terminal
        escaped_data = json.dumps(data)
        js_code = f"window.writeToTerminal({escaped_data})"
        self.web_view.page().runJavaScript(js_code)
    
    def _load_notification_sound(self):
        """Load the notification sound file."""
        # Look for sound file in assets directory
        sound_path = Path(__file__).parent.parent / "assets" / "done.wav"
        if sound_path.exists():
            self.sound_effect.setSource(QUrl.fromLocalFile(str(sound_path)))
            self.sound_effect.setVolume(0.5)
        else:
            pass  # Notification sound not found
    
    def _on_inactivity_detected(self):
        """Handle inactivity detection - play a sound."""
        # Play the sound effect from PySide6
        if self.sound_effect.source():
            self.sound_effect.play()
    
    def closeEvent(self, event):
        """Clean up when closing."""
        self.bridge.cleanup()
        super().closeEvent(event)
    
    def cleanup(self):
        """Clean up resources."""
        self.bridge.cleanup()