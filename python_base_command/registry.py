"""
Manual command registry.

Allows registering commands by name and running them from a single entry point,
without relying on the auto-discovery folder convention.

Usage::

    from python_base_command import BaseCommand, CommandRegistry

    registry = CommandRegistry()

    @registry.register("greet")
    class GreetCommand(BaseCommand):
        help = "Greet someone"

        def add_arguments(self, parser):
            parser.add_argument("name")

        def handle(self, *args, **options):
            self.stdout.write(self.style.SUCCESS(f"Hello, {options['name']}!"))

    if __name__ == "__main__":
        registry.run()
"""

import os
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

from custom_python_logger import get_logger

from python_base_command.const import CURRENT_DATE_TIME_STR

if TYPE_CHECKING:
    from python_base_command.base import BaseCommand as BaseCommandType


class CommandRegistry:
    """
    A registry that maps command names to ``BaseCommand`` subclasses and
    exposes a single ``run()`` entry point.
    """

    def __init__(self) -> None:
        self.logger = get_logger(
            name=os.getenv("PYTHON_BASE_COMMAND_PROJECT_NAME", f"{self.__class__.__name__}__{CURRENT_DATE_TIME_STR}")
        )

        self._commands: dict[str, type[BaseCommandType]] = {}

    def register(self, name: str) -> Callable[[type["BaseCommandType"]], type["BaseCommandType"]]:
        """
        Class decorator that registers a ``BaseCommand`` subclass under *name*.

        Usage::

            @registry.register("greet")
            class GreetCommand(BaseCommand):
                ...
        """

        def decorator(cls: type["BaseCommandType"]) -> type["BaseCommandType"]:
            self._commands[name] = cls
            return cls

        return decorator

    def add(self, name: str, command_class: type["BaseCommandType"]) -> None:
        """
        Programmatically register *command_class* under *name*.
        """
        self._commands[name] = command_class

    def get(self, name: str) -> type["BaseCommandType"] | None:
        """Return the command class registered under *name*, or ``None``."""
        return self._commands.get(name)

    def list_commands(self) -> list[str]:
        """Return a sorted list of registered command names."""
        return sorted(self._commands)

    def run(self, argv: list[str] | None = None) -> None:
        """
        Parse *argv* (defaults to ``sys.argv``), find the requested command,
        and run it.

        The expected argv format is::

            [prog, subcommand, ...args...]

        e.g. ``["myapp", "greet", "Alice", "--shout"]``
        """

        argv = argv or sys.argv[:]

        # Show top-level help if no subcommand is given.
        if len(argv) < 2 or argv[1] in {"-h", "--help"}:
            self._print_help(argv[0] if argv else "unknown")
            sys.exit(0)

        subcommand = argv[1]
        if (command_class := self._commands.get(subcommand)) is None:
            prog = argv[0] if argv else "unknown"
            available = ", ".join(self.list_commands()) or "(none registered)"
            self.logger.error(
                f"Unknown command: '{subcommand}'. "
                f"Available commands: {available}. "
                f"Type '{prog} --help' for usage."
            )
            sys.exit(1)
        command_class().run_from_argv([argv[0]] + argv[2:])

    def _print_help(self, prog: str) -> None:
        print(f"Usage: {prog} <command> [options]\n")
        print("Available commands:")
        for name in self.list_commands():
            cls = self._commands[name]
            desc = cls.help or "(no description)"
            print(f"  {name:<20} {desc}")
        print(f"\nRun '{prog} <command> --help' for command-specific help.")
