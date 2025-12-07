import os
import sys

from ui.terminal_pane import TerminalPane


def _sep() -> str:
    return os.pathsep


def test_remove_path_entry_exact_match():
    sep = _sep()
    path_value = sep.join(["/usr/bin", "/app/.venv/bin", "/usr/local/bin"])
    cleaned = TerminalPane._remove_path_entry(path_value, "/app/.venv/bin")
    assert cleaned == sep.join(["/usr/bin", "/usr/local/bin"])


def test_remove_path_entry_multiple_occurrences():
    sep = _sep()
    path_value = sep.join(["/app/.venv/bin", "/usr/bin", "/app/.venv/bin", "/usr/local/bin"])
    cleaned = TerminalPane._remove_path_entry(path_value, "/app/.venv/bin")
    assert cleaned == sep.join(["/usr/bin", "/usr/local/bin"])


def test_remove_path_entry_missing_or_empty():
    sep = _sep()
    original = sep.join(["/usr/bin", "/usr/local/bin"])

    # Entry not present: unchanged
    cleaned = TerminalPane._remove_path_entry(original, "/does/not/exist")
    assert cleaned == original

    # Empty PATH stays empty
    assert TerminalPane._remove_path_entry("", "/something") == ""

    # Empty entry: PATH unchanged
    assert TerminalPane._remove_path_entry(original, "") == original
