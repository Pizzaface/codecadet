"""Application-wide constants.

This module centralizes magic numbers and configuration values to improve
maintainability and reduce code duplication.
"""

# Terminal configuration
TERMINAL_CHAR_WIDTH = 7
TERMINAL_CHAR_HEIGHT = 14
TERMINAL_MIN_COLS = 40
TERMINAL_MIN_ROWS = 10
TERMINAL_CONTAINER_PADDING = 20

# Notification sound configuration
NOTIFICATION_SOUND_RATE_LIMIT_SECONDS = 4.0
NOTIFICATION_SOUND_VOLUME = 0.5

# Window geometry
DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 600
MIN_WINDOW_WIDTH = 880
MIN_WINDOW_HEIGHT = 520

# Splitter proportions
SIDEBAR_INITIAL_WIDTH = 400
TERMINAL_PANE_INITIAL_WIDTH = 600

# Font configuration
DEFAULT_FONT_FAMILY = "Arial"
DEFAULT_FONT_SIZE = 11
TERMINAL_FONT_FAMILY = "Monospace"
TERMINAL_FONT_SIZE = 11
CODE_FONT_FAMILY = "Consolas"

# Auto-refresh delay (milliseconds)
AUTO_REFRESH_DELAY_MS = 100
AUTO_REFRESH_STATUS_DELAY_MS = 200

# Path truncation
MAX_PATH_DISPLAY_LENGTH = 50
PATH_TRUNCATION_PREFIX = "..."

# UI text
APP_TITLE = "Git Worktree Manager for Claude Code"
APP_VERSION = "2.0"
APP_ABOUT_TEXT = """Worktree Manager for Claude Code — v2
• Multi-session terminal support
• Recents + auto‑reopen
• Modern dark UI
• Embedded terminal via xterm on Linux
Built with PySide6 for cross-platform compatibility."""

# Status messages
STATUS_READY = "Ready"
STATUS_NO_SESSION = "No active session"

# Locale settings
DEFAULT_LOCALE = "en_US.UTF-8"

# Common developer tool paths (for PATH augmentation in terminals)
COMMON_DEVELOPER_PATHS = [
    "$HOME/.local/bin",
    "$HOME/.poetry/bin",
    "$HOME/.pyenv/bin",
    "$HOME/.pyenv/shims",
    "$HOME/.asdf/bin",
    "$HOME/.asdf/shims",
    "$HOME/.rtx/bin",
    "$HOME/.deno/bin",
    "$HOME/.cargo/bin",
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
]

# Graphite attention indicator color
ATTENTION_INDICATOR_COLOR = "#f4be6c"
ATTENTION_INDICATOR_CHAR = "●"

# Git branch prefixes to remove
GIT_BRANCH_PREFIX_REFS_HEADS = "refs/heads/"
GIT_BRANCH_PREFIX_REMOTES_ORIGIN = "remotes/origin/"

# Status message icons
ICON_FOLDER = "📂"
ICON_FILE = "🗂️"
ICON_SUCCESS = "✅"
ICON_DELETE = "🗑️"
ICON_CLEAN = "🧹"
ICON_SETTINGS = "⚙️"
ICON_ROBOT = "🤖"
ICON_GRAPHITE = "📊"
ICON_WARNING = "⚠️"

# Button text prefixes
BUTTON_PREFIX_RUN = "▶"
BUTTON_PREFIX_EXTERNAL = "□"
BUTTON_PREFIX_STOP = "⛔"

# Environment variable names for terminal cleanup
ENV_VAR_VIRTUAL_ENV = "VIRTUAL_ENV"
ENV_VAR_POETRY_ACTIVE = "POETRY_ACTIVE"
ENV_VAR_PATH = "PATH"
ENV_VAR_LANG = "LANG"
ENV_VAR_LC_ALL = "LC_ALL"
ENV_VAR_LC_CTYPE = "LC_CTYPE"
ENV_VAR_PYTHONIOENCODING = "PYTHONIOENCODING"

# Geometry calculation
GEOMETRY_WIDTH_INDEX = 0
GEOMETRY_HEIGHT_INDEX = 1
