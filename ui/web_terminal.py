"""Web-based terminal widget using xterm.js for better character handling."""

import os
import pty
import select
import json
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QObject, Slot, Signal, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QWidget, QVBoxLayout


class TerminalBridge(QObject):
    """Bridge between the web terminal and PTY."""
    
    data_received = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.master_fd = None
        self.process_pid = None
        self.reader_thread = None
        self.running = False
        
    def start_pty(self, command, cwd):
        """Start PTY process."""
        try:
            pid, fd = pty.fork()
            
            if pid == 0:  # Child process
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
            print(f"Failed to start PTY: {e}")
            return False
    
    def _read_pty(self):
        """Read from PTY in background thread."""
        while self.running and self.master_fd:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if r:
                    data = os.read(self.master_fd, 4096)
                    if data:
                        # Decode and emit data
                        text = data.decode('utf-8', errors='replace')
                        self.data_received.emit(text)
                    else:
                        break
            except OSError:
                break
    
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
                print(f"Resized PTY to {cols}x{rows}")
            except OSError as e:
                print(f"Failed to resize PTY: {e}")
    
    def cleanup(self):
        """Clean up PTY resources."""
        self.running = False
        
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
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #000;
            font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', 'DejaVu Sans Mono', monospace;
        }
        #terminal {
            width: 100%;
            height: 100vh;
            background-color: #000;
        }
    </style>
</head>
<body>
    <div id="terminal"></div>
    
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    
    <script>
        // Create terminal instance
        const terminal = new Terminal({
            theme: {
                background: '#000000',
                foreground: '#ffffff',
                cursor: '#ffffff',
                cursorAccent: '#000000',
                selection: '#333333',
                black: '#000000',
                red: '#cd3131',
                green: '#0dbc79',
                yellow: '#e5e510',
                blue: '#2472c8',
                magenta: '#bc3fbc',
                cyan: '#11a8cd',
                white: '#e5e5e5',
                brightBlack: '#666666',
                brightRed: '#f14c4c',
                brightGreen: '#23d18b',
                brightYellow: '#f5f543',
                brightBlue: '#3b8eea',
                brightMagenta: '#d670d6',
                brightCyan: '#29b8db',
                brightWhite: '#ffffff'
            },
            fontSize: 12,  // Slightly larger font
            fontFamily: '"SF Mono", "Monaco", "Menlo", "Consolas", "DejaVu Sans Mono", monospace',
            cursorBlink: true,
            cursorStyle: 'block',
            scrollback: 10000,
            tabStopWidth: 4,
            convertEol: true,
            cols: 120,  // Default columns
            rows: 30,   // Default rows
            allowTransparency: false,
            bellStyle: 'none'
        });
        
        // Add addons
        const fitAddon = new FitAddon.FitAddon();
        const webLinksAddon = new WebLinksAddon.WebLinksAddon();
        
        terminal.loadAddon(fitAddon);
        terminal.loadAddon(webLinksAddon);
        
        // Open terminal
        terminal.open(document.getElementById('terminal'));
        fitAddon.fit();
        
        // Set up Qt WebChannel communication
        let qtBridge = null;
        new QWebChannel(qt.webChannelTransport, function (channel) {
            qtBridge = channel.objects.qtBridge;
            console.log('Qt WebChannel connected');
        });
        
        // Handle input from terminal
        terminal.onData(data => {
            if (qtBridge) {
                qtBridge.write_to_pty(data);
            } else {
                console.log('Qt bridge not ready, data:', data);
            }
        });
        
        // Handle resize with PTY size update
        window.addEventListener('resize', () => {
            setTimeout(() => {
                fitAddon.fit();
                const dims = fitAddon.proposeDimensions();
                if (dims && qtBridge) {
                    qtBridge.resize_pty(dims.cols, dims.rows);
                }
            }, 100);
        });
        
        // Fit terminal on load and ensure proper sizing
        setTimeout(() => {
            fitAddon.fit();
            // Send terminal size to PTY
            const dims = fitAddon.proposeDimensions();
            if (dims && qtBridge) {
                qtBridge.resize_pty(dims.cols, dims.rows);
            }
        }, 100);
        
        // Additional resize attempts to ensure proper sizing
        setTimeout(() => {
            fitAddon.fit();
            const dims = fitAddon.proposeDimensions();
            if (dims && qtBridge) {
                qtBridge.resize_pty(dims.cols, dims.rows);
            }
        }, 500);
        
        setTimeout(() => {
            fitAddon.fit();
            const dims = fitAddon.proposeDimensions();
            if (dims && qtBridge) {
                qtBridge.resize_pty(dims.cols, dims.rows);
            }
        }, 1000);
        
        // Global function to write data to terminal
        window.writeToTerminal = function(data) {
            terminal.write(data);
        };
        
        // Focus terminal
        terminal.focus();
        
        console.log('Terminal initialized');
    </script>
</body>
</html>
        """
    
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
    
    def closeEvent(self, event):
        """Clean up when closing."""
        self.bridge.cleanup()
        super().closeEvent(event)
    
    def cleanup(self):
        """Clean up resources."""
        self.bridge.cleanup()