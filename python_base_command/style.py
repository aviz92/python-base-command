"""
Terminal color styles, mirroring Django's management color system.
"""

import os
import sys

ANSI_COLORS = {
    "SUCCESS": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "NOTICE": "\033[34m",  # blue
    "SQL_FIELD": "\033[32;1m",  # bold green
    "SQL_COLTYPE": "\033[33m",  # yellow
    "SQL_KEYWORD": "\033[34;1m",  # bold blue
    "SQL_TABLE": "\033[36m",  # cyan
    "HTTP_INFO": "\033[34m",  # blue
    "HTTP_SUCCESS": "\033[32m",  # green
    "HTTP_REDIRECT": "\033[33m",  # yellow
    "HTTP_NOT_MODIFIED": "\033[36m",  # cyan
    "HTTP_BAD_REQUEST": "\033[31;1m",  # bold red
    "HTTP_NOT_FOUND": "\033[31m",  # red
    "HTTP_SERVER_ERROR": "\033[41;1m",  # bold red bg
    "MIGRATE_HEADING": "\033[34;1m",  # bold blue
    "MIGRATE_LABEL": "\033[35m",  # magenta
    "RESET": "\033[0m",
}


def _supports_color() -> bool:
    """Return True if the terminal supports ANSI color codes."""
    if os.environ.get("NO_COLOR") or os.environ.get("BASE_COMMAND_NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") or os.environ.get("BASE_COMMAND_FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Style:
    """
    Holds callable style functions (one per named style).
    Each function wraps a string in the appropriate ANSI codes,
    or is a no-op if color is disabled.
    """

    def __init__(self, use_color: bool = True):
        self._use_color = use_color
        for name, code in ANSI_COLORS.items():
            if name == "RESET":
                continue
            if use_color:
                setattr(self, name, self._make_styler(code))
            else:
                setattr(self, name, self._noop)

    @staticmethod
    def _make_styler(code: str):
        def styler(text: str) -> str:
            return f"{code}{text}{ANSI_COLORS['RESET']}"

        return styler

    @staticmethod
    def _noop(text: str) -> str:
        return text


def color_style(force_color: bool = False) -> Style:
    """Return a Style object that uses color if supported (or forced)."""
    use_color = force_color or _supports_color()
    return Style(use_color=use_color)


def no_style() -> Style:
    """Return a Style object with all styling disabled."""
    return Style(use_color=False)
