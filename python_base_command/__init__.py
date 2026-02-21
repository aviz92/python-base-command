"""
base-command
============

A Django-style BaseCommand framework for standalone Python CLI tools.

Public API
----------
- BaseCommand      — base class for all commands
- LabelCommand     — base class for commands that accept one or more labels
- CommandError     — exception to signal a clean error exit
- CommandParser    — customized ArgumentParser used internally
- OutputWrapper    — stdout/stderr wrapper with style support
- CommandRegistry  — manual command registry (decorator-based)
- Runner           — auto-discovery runner (folder-based, like manage.py)
- call_command     — programmatic command invocation (like Django's)
"""

from .base import (
    BaseCommand,
    CommandError,
    CommandParser,
    LabelCommand,
)
from .output import OutputWrapper
from .registry import CommandRegistry
from .runner import Runner
from .style import Style, color_style, no_style
from .utils import call_command

__all__ = [
    "BaseCommand",
    "CommandError",
    "CommandParser",
    "CommandRegistry",
    "LabelCommand",
    "OutputWrapper",
    "Runner",
    "Style",
    "call_command",
    "color_style",
    "no_style",
]

__version__ = "0.1.0"
