"""
python-base-command
===================

A Django-style BaseCommand framework for standalone Python CLI tools.

Public API
----------
- BaseCommand      — base class for all commands (use self.logger for output)
- LabelCommand     — base class for commands that accept one or more labels
- CommandError     — exception to signal a clean error exit
- CommandParser    — customized ArgumentParser used internally
- CommandRegistry  — manual command registry (decorator-based)
- Runner           — auto-discovery runner (folder-based, like manage.py)
- call_command     — programmatic command invocation
"""

from custom_python_logger import build_logger

from .base import (
    BaseCommand,
    CommandError,
    CommandParser,
    LabelCommand,
)
from .registry import CommandRegistry
from .runner import Runner
from .utils import call_command

__all__ = [
    "BaseCommand",
    "CommandError",
    "CommandParser",
    "CommandRegistry",
    "LabelCommand",
    "Runner",
    "call_command",
]

build_logger(
    project_name="python-base-command",
    log_format="%(asctime)s | %(levelname)s | %(message)s",
)
