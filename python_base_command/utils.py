"""
call_command — invoke a command programmatically.

Mirrors Django's django.core.management.call_command.

Usage::

    from python_base_command import call_command, CommandError

    call_command(GreetCommand, name="Alice")
"""

from typing import Any

from .base import BaseCommand


def call_command(
    command: "type[BaseCommand] | BaseCommand",
    *args: Any,
    **options: Any,
) -> Any:
    """
    Call the given BaseCommand subclass (or instance) programmatically.

    Parameters
    ----------
    command:
        A BaseCommand subclass or an already-instantiated command object.
    *args:
        Positional arguments forwarded to handle().
    **options:
        Keyword arguments forwarded to execute().

    Returns
    -------
    Whatever handle() returns.

    Raises
    ------
    CommandError
        Propagated from handle() so callers can handle it themselves.
    TypeError
        If *command* is a type that is not a ``BaseCommand`` subclass.
    """
    if isinstance(command, type):
        if not issubclass(command, BaseCommand):
            raise TypeError(f"command must be a BaseCommand subclass, got {type(command)}")
        command = command()

    options.setdefault("verbosity", 1)
    options.setdefault("traceback", False)

    return command.execute(*args, **options)
