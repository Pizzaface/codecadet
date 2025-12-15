"""Web-based terminal widget using xterm.js for better character handling."""

import os
import sys
import select
import json
import threading
import time
import base64
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QObject, Slot, Signal, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtMultimedia import QSoundEffect

# Platform-specific PTY imports
if sys.platform.startswith("win"):
    try:
        from winpty import PtyProcess
    except ImportError:
        PtyProcess = None
else:
    import pty

INACTIVITY_TIMER = 3


class TerminalBridge(QObject):
    """Bridge between the web terminal and PTY."""
    
    data_received = Signal(str)
    inactivity_detected = Signal()  # Signal when no output for 10 seconds
    activity = Signal()  # Fires on any input or output
    
    def __init__(self):
        super().__init__()
        self.master_fd = None
        self.process = None  # Store winpty process on Windows
        self.process_pid = None
        self.reader_thread = None
        self.running = False
        self.last_output_time = None
        self.last_input_time = None
        self._activity_seen = False  # Gate inactivity until first activity
        self.tracking_enabled = False  # Do not track until armed by submit (Enter)
        self._awaiting_output = False  # After submit, wait for first output before timing
        self.inactivity_timer = QTimer()
        self.inactivity_timer.timeout.connect(self._check_inactivity)
        self.inactivity_timer.start(1000)  # Check every second
        self.inactivity_triggered = False
        
    def start_pty(self, command, cwd):
        """Start PT process."""
        import sys
        if sys.platform.startswith("win"):
            # Windows implementation using pywinpty
            if not PtyProcess:
                print("PtyProcess is None")
                return False
            
            print(f"Starting terminal with command: {command}")
            print(f"Working directory: {cwd}")
            
            # Create winpty process using PtyProcess.spawn
            try:
                self.process = PtyProcess.spawn(command, cwd=str(cwd))
            except Exception as e:
                print(f"PtyProcess.spawn failed with exception: {e}")
                return False
            
            if self.process is None:
                print("PtyProcess.spawn returned None")
                return False
            
            # Check if the process has a valid PID
            if not hasattr(self.process, 'pid') or self.process.pid is None:
                print("Process has no valid PID")
                return False
            
            self.process_pid = self.process.pid
            self.running = True

            # Set initial PTY size immediately
            # This is critical - many CLIs query terminal size on startup
            initial_rows, initial_cols = 30, 120
            try:
                self.process.setwinsize(initial_rows, initial_cols)
            except Exception:
                pass  # setwinsize may not be available on all winpty versions

            # Start reader thread
            self.reader_thread = threading.Thread(target=self._read_pty)
            self.reader_thread.daemon = True
            self.reader_thread.start()

            return True
        else:
            # Unix implementation using pty
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

                # Set initial PTY size via ioctl BEFORE any reads
                # This is critical - many CLIs query TIOCGWINSZ immediately on startup
                # and won't use COLUMNS/LINES env vars. Without this, they get 0x0.
                import fcntl
                import struct
                import termios
                initial_rows, initial_cols = 30, 120  # Match env var defaults
                s = struct.pack('HHHH', initial_rows, initial_cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, s)

                # Start reader thread
                self.reader_thread = threading.Thread(target=self._read_pty)
                self.reader_thread.daemon = True
                self.reader_thread.start()

                return True

    def _read_pty(self):
        """Read from PTY in background thread."""
        while self.running and (self.master_fd or self.process):
            try:
                if sys.platform.startswith("win") and self.process:
                    # Windows: read from winpty process
                    # Check if process is still alive before attempting to read
                    if not self.process.isalive():
                        break
                    
                    # Use a smaller read size to avoid blocking
                    data = self.process.read(1024)
                    if data:
                        # Update last output time and reset inactivity flag
                        self.last_output_time = time.time()
                        self._activity_seen = True
                        if self.tracking_enabled:
                            # First output after submit: start timing window
                            self._awaiting_output = False
                            self.inactivity_triggered = False
                        # Indicate activity (output)
                        self.activity.emit()
                        # Emit base64 to preserve bytes and escape sequences
                        b64 = base64.b64encode(data.encode('utf-8', errors='replace')).decode('ascii')
                        self.data_received.emit(b64)
                    else:
                        time.sleep(0.01)  # Small delay to prevent busy loop
                else:
                    # Unix: use select to read from PTY
                    r, _, _ = select.select([self.master_fd], [], [], 0.1)
                    if r:
                        data = os.read(self.master_fd, 4096)
                        if data:
                            # Update last output time and reset inactivity flag
                            self.last_output_time = time.time()
                            self._activity_seen = True
                            if self.tracking_enabled:
                                # First output after submit: start timing window
                                self._awaiting_output = False
                                self.inactivity_triggered = False
                            # Indicate activity (output)
                            self.activity.emit()
                            # Emit base64 to preserve bytes and escape sequences
                            b64 = base64.b64encode(data).decode('ascii')
                            self.data_received.emit(b64)
                        else:
                            break
            except (OSError, EOFError):
                break
            except Exception:
                # Handle any other exceptions that might occur
                break
    
    def _check_inactivity(self):
        """Check if there's been no output for the timeout after a submit."""
        if not self.tracking_enabled:
            return
        # Don't consider inactivity until after we see first output post-submit
        if self._awaiting_output:
            return
        if not self.inactivity_triggered and self._activity_seen:
            now = time.time()

            # If the user is still interacting with the terminal (typing, navigation
            # keys, etc.), treat that as activity and defer inactivity notification.
            if self.last_input_time and (now - self.last_input_time) < INACTIVITY_TIMER:
                return

            # Only consider last output time once we're outside the interaction window
            if self.last_output_time and (now - self.last_output_time) >= INACTIVITY_TIMER:
                self.inactivity_triggered = True
                # Stop checking until the next explicit submit (Enter)
                # This ensures we only notify once per user-submitted request.
                self.tracking_enabled = False
                self.inactivity_detected.emit()
    
    @Slot(str)
    def write_to_pty(self, data):
        """Write data to PTY."""
        # Mark input activity for UI, but don't reset inactivity timer on input
        self.last_input_time = time.time()
        self._activity_seen = True
        # If user submitted (pressed Enter), arm tracking for this request
        if '\r' in data:
            self.tracking_enabled = True
            self._awaiting_output = True
            self.inactivity_triggered = False
            # Clear last_output_time so we only start timing after first output
            self.last_output_time = None
        # Indicate activity (input)
        self.activity.emit()

        if (self.master_fd or self.process) and data:
            try:
                if sys.platform.startswith("win") and self.process:
                    # Windows: write to winpty process
                    self.process.write(data)
                else:
                    # Unix: write to PTY
                    os.write(self.master_fd, data.encode('utf-8'))
            except OSError:
                pass

    def enable_tracking(self):
        """Arm inactivity tracking from now on."""
        # Keep available for manual arming, but prefer Enter-based arming.
        self.tracking_enabled = True
        now = time.time()
        self.last_input_time = now
        # Defer timing until first output to avoid false positives
        self.last_output_time = None
        self._awaiting_output = True
        self.inactivity_triggered = False
    
    @Slot(int, int)
    def resize_pty(self, cols, rows):
        """Resize the PTY."""
        if sys.platform.startswith("win") and self.process:
            # Windows: resize winpty process
            self.process.setwinsize(cols, rows)
        elif self.master_fd:
            # Unix: resize PTY
            import fcntl
            import struct
            import termios
            # Set the terminal size
            s = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, s)
    
    def cleanup(self):
        """Clean up PTY resources."""
        self.running = False
        self.inactivity_timer.stop()
        
        if self.reader_thread:
            self.reader_thread.join(timeout=1.0)
        
        if sys.platform.startswith("win") and self.process:
            # Windows: clean up winpty process
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None
            self.master_fd = None
        else:
            # Unix: clean up PTY
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
    inactivity_for_worktree = Signal(str)  # Emits worktree path on inactivity
    activity_for_worktree = Signal(str)    # Emits worktree path on activity
    
    def __init__(self, parent, command, cwd):
        super().__init__(parent)
        
        # Remember which worktree this widget is for
        self.cwd_path = str(cwd)
        
        # Track if terminal started successfully
        self._terminal_started = False

        self.bridge = TerminalBridge()
        self.bridge.data_received.connect(self._on_data_received)
        self.bridge.inactivity_detected.connect(self._on_inactivity_detected)
        self.bridge.activity.connect(self._on_activity)
        
        # Setup sound effect for inactivity notification
        self.sound_effect = QSoundEffect()
        self._last_sound_time = 0.0
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
            self._terminal_started = True
            self.web_view.page().runJavaScript("console.log('PTY started successfully')")
            # Trigger a resize to sync PTY with actual container dimensions
            QTimer.singleShot(200, self._trigger_initial_resize)
        else:
            self._terminal_started = False
            self.web_view.page().runJavaScript("window.writeToTerminal('Failed to start terminal session\\r\\n')")

    def _trigger_initial_resize(self):
        """Trigger initial resize to sync PTY with container dimensions."""
        # Force a resize to match the actual widget dimensions
        self.web_view.page().runJavaScript("if (typeof handleResize === 'function') { handleResize(true); }")
    
    def is_terminal_started(self):
        """Check if the terminal started successfully."""
        return self._terminal_started
    
    def _on_data_received(self, data):
        """Handle data received from PTY (base64-encoded bytes)."""
        # Data is base64 string; pass directly to the JS base64 writer
        escaped_b64 = json.dumps(data)
        js_code = f"window.writeToTerminalBase64({escaped_b64})"
        self.web_view.page().runJavaScript(js_code)
        # No auto-arming here; arming occurs on Enter in write_to_pty
        
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
        # Notify listeners (e.g., main window/sidebar) with the worktree path
        # Sound is now handled centrally in the main window alongside the visual indicator.
        self.inactivity_for_worktree.emit(self.cwd_path)

    def _on_activity(self):
        """Bridge reported activity (input/output) — bubble up with path."""
        # Do not auto-arm tracking here; rely on Enter-based arming
        self.activity_for_worktree.emit(self.cwd_path)
    
    def closeEvent(self, event):
        """Clean up when closing."""
        self.bridge.cleanup()
        super().closeEvent(event)
    
    def cleanup(self):
        """Clean up resources."""
        self.bridge.cleanup()
