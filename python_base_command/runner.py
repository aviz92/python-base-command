"""
Auto-discovery runner.

Discovers ``BaseCommand`` subclasses from a ``commands/`` directory
(or any directory you point it at) and exposes a single ``run()``
entry point — exactly like Django's ``manage.py``.

Convention
----------
Each Python module inside the commands directory must define a class
named ``Command`` that extends ``BaseCommand``.  Files whose names start
with an underscore are ignored.

Usage::

    # myapp/cli.py
    from base_command.runner import Runner

    runner = Runner(commands_dir="commands")   # relative to this file

    if __name__ == "__main__":
        runner.run()

Then create ``commands/greet.py``::

    from base_command import BaseCommand, CommandError

    class Command(BaseCommand):
        help = "Greet someone"

        def add_arguments(self, parser):
            parser.add_argument("name")

        def handle(self, *args, **options):
            self.stdout.write(self.style.SUCCESS(f"Hello, {options['name']}!"))

And run::

    python cli.py greet Alice
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType

from custom_python_logger import build_logger

from .base import BaseCommand

logger = build_logger(project_name="python-base-command")


class Runner:
    """
    Discovers and runs commands from a directory of Python modules.

    Parameters
    ----------
    commands_dir:
        Path to the directory containing command modules.  Can be absolute
        or relative to the *caller's* file.
    caller_file:
        The ``__file__`` of the script that instantiates ``Runner``.
        Used only to resolve a relative *commands_dir*.  Defaults to the
        file of the direct caller of ``Runner.__init__()``.
    """

    def __init__(
        self,
        commands_dir: str | Path = "commands",
        caller_file: str | None = None,
    ) -> None:
        if caller_file is None:
            frame = inspect.stack()[1]
            caller_file = frame.filename

        base = Path(caller_file).parent
        self._commands_dir = (base / commands_dir).resolve()

    # ------------------------------------------------------------------ discovery

    def _discover(self) -> dict[str, type[BaseCommand]]:
        """
        Walk ``self._commands_dir`` and import every non-private module that
        exposes a ``Command`` class inheriting from ``BaseCommand``.
        """
        commands: dict[str, type[BaseCommand]] = {}

        if not self._commands_dir.is_dir():
            return commands

        for path in sorted(self._commands_dir.glob("*.py")):
            if path.stem.startswith("_"):
                continue

            if (module := self._load_module(path)) is None:
                continue

            if (command_class := getattr(module, "Command", None)) is None:
                continue
            if not (isinstance(command_class, type) and issubclass(command_class, BaseCommand)):
                continue

            commands[path.stem] = command_class

        return commands

    @staticmethod
    def _load_module(path: Path) -> ModuleType | None:
        """Dynamically load a Python file as a module."""
        module_name = f"_base_command_discovered_.{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.error(f"Error loading command module '{path}': {exc}")
            return None
        return module

    # ------------------------------------------------------------------ running

    def run(self, argv: list[str] | None = None) -> None:
        """
        Parse *argv* (defaults to ``sys.argv``), discover commands, find the
        requested one, and run it.
        """
        argv = argv or sys.argv[:]
        commands = self._discover()

        # Show top-level help if no subcommand is given.
        if len(argv) < 2 or argv[1] in {"-h", "--help"}:
            self._print_help(argv[0] if argv else "unknown", commands)
            sys.exit(0)

        subcommand = argv[1]
        if (command_class := commands.get(subcommand)) is None:
            prog = argv[0] if argv else "unknown"
            available = ", ".join(sorted(commands)) or "(none found)"
            logger.error(
                f"Unknown command: '{subcommand}'. "
                f"Available commands: {available}. "
                f"Type '{prog} --help' for usage."
            )
            sys.exit(1)
        command_class().run_from_argv([argv[0]] + argv[2:])

    @staticmethod
    def _print_help(prog: str, commands: dict[str, type[BaseCommand]]) -> None:
        print(f"Usage: {prog} <command> [options]\n")
        print("Available commands:")
        for name, cls in sorted(commands.items()):
            desc = cls.help or "(no description)"
            print(f"  {name:<20} {desc}")
        print(f"\nRun '{prog} <command> --help' for command-specific help.")
