"""
``call_command`` — invoke a command programmatically.

Mirrors Django's ``django.core.management.call_command``.

Usage::

    from python_base_command import call_command, CommandError

    # Pass a command class directly:
    call_command(GreetCommand, "Alice", verbosity=0)

    # Or pass the class, keyword-only:
    call_command(GreetCommand, name="Alice", shout=True)
"""

from typing import Any

from .base import BaseCommand


def call_command(
    command: "type[BaseCommand] | BaseCommand",
    *args: Any,
    **options: Any,
) -> Any:
    """
    Call the given ``BaseCommand`` subclass (or instance) programmatically.

    Parameters
    ----------
    command:
        Either a ``BaseCommand`` subclass *or* an already-instantiated
        command object.
    *args:
        Positional arguments forwarded to ``handle()``.
    **options:
        Keyword arguments forwarded to ``execute()``.

    Returns
    -------
    Whatever ``handle()`` returns.

    Raises
    ------
    CommandError
        Propagated from ``handle()`` so that callers can decide how to
        handle it (unlike CLI invocation, where it is caught and printed).
    """
    if isinstance(command, type):
        command = command()

    # Ensure base options have sensible defaults so execute() doesn't KeyError.
    options.setdefault("verbosity", 1)
    options.setdefault("no_color", False)
    options.setdefault("force_color", False)
    options.setdefault("traceback", False)

    return command.execute(*args, **options)
