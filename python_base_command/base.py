"""
Base classes for writing CLI commands outside of Django.

Mirrors Django's django.core.management.base as closely as possible,
stripping out Django-specific concepts (DB, migrations, apps, translations)
while keeping the full command-parsing and execution machinery.
"""

import argparse
import os
import sys
from argparse import ArgumentParser, HelpFormatter
from collections.abc import Sequence
from typing import Any

from .output import OutputWrapper
from .style import Style, color_style, no_style

__all__ = [
    "BaseCommand",
    "CommandError",
    "CommandParser",
    "LabelCommand",
    "OutputWrapper",
]

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CommandError(Exception):
    """
    Exception class indicating a problem while executing a command.

    If this exception is raised during command execution it will be caught
    and turned into a nicely-printed error message to stderr; raising it
    (with a sensible description) is the preferred way to signal that
    something has gone wrong.

    ``returncode`` controls the process exit code (default 1).
    """

    def __init__(self, *args: Any, returncode: int = 1, **kwargs: Any):
        self.returncode = returncode
        super().__init__(*args, **kwargs)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


class CommandParser(ArgumentParser):
    """
    Customized ArgumentParser that:
    - Improves missing-argument error messages.
    - Raises CommandError instead of calling sys.exit() when the command is
      invoked programmatically (not from the CLI).
    """

    def __init__(
        self,
        *,
        missing_args_message: str | None = None,
        called_from_command_line: bool | None = None,
        **kwargs: Any,
    ):
        self.missing_args_message = missing_args_message
        self.called_from_command_line = called_from_command_line
        super().__init__(**kwargs)

    def parse_args(  # type: ignore[override]
        self,
        args: Sequence[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ) -> argparse.Namespace:
        if self.missing_args_message and not (args or any(not arg.startswith("-") for arg in (args or []))):
            self.error(self.missing_args_message)
        return super().parse_args(args, namespace)

    def error(self, message: str) -> None:  # type: ignore[override]
        if self.called_from_command_line:
            super().error(message)
        else:
            raise CommandError("Error: %s" % message)


# ---------------------------------------------------------------------------
# Help formatter
# ---------------------------------------------------------------------------


class CommandHelpFormatter(HelpFormatter):
    """
    Customized HelpFormatter that pushes the common base arguments
    (--version, --verbosity, etc.) to the bottom of the help output so
    that command-specific arguments appear first — exactly as Django does.
    """

    show_last: set[str] = {
        "--version",
        "--verbosity",
        "--traceback",
        "--no-color",
        "--force-color",
    }

    def _reordered_actions(self, actions: list[argparse.Action]) -> list[argparse.Action]:
        return sorted(
            actions,
            key=lambda a: bool(set(a.option_strings) & self.show_last),
        )

    def add_usage(self, usage, actions, *args, **kwargs):  # type: ignore[override]
        super().add_usage(usage, self._reordered_actions(actions), *args, **kwargs)

    def add_arguments(self, actions):  # type: ignore[override]
        super().add_arguments(self._reordered_actions(actions))


# ---------------------------------------------------------------------------
# BaseCommand
# ---------------------------------------------------------------------------


class BaseCommand:
    """
    The base class from which all commands derive.

    Mirrors Django's ``BaseCommand`` without any Django-specific machinery
    (no database, no migrations, no app registry, no translation layer).

    Execution flow
    --------------
    1. ``run_from_argv()`` is called with ``sys.argv``.
    2. It calls ``create_parser()`` to build an ``ArgumentParser``, then
       parses the arguments and calls ``execute()``.
    3. ``execute()`` calls ``handle()`` with the parsed options.
    4. Any ``CommandError`` raised in ``handle()`` is caught by
       ``run_from_argv()``, printed to *stderr*, and the process exits with
       the error's ``returncode``.

    Attributes
    ----------
    help : str
        Short description printed in ``--help`` output.
    output_transaction : bool
        If ``True``, wrap any string returned by ``handle()`` with
        ``BEGIN;`` / ``COMMIT;`` markers (useful for SQL-generating tools).
        Default: ``False``.
    suppressed_base_arguments : set[str]
        Option strings (e.g. ``{"--traceback"}``) whose help text should be
        suppressed (replaced with ``argparse.SUPPRESS``) in the output.
    stealth_options : tuple[str, ...]
        Names of options the command uses that are *not* declared via
        ``add_arguments()``.  They won't cause unknown-option errors when
        ``call_command()`` is used.
    missing_args_message : str | None
        Custom error message when required positional arguments are missing.
    """

    # ------------------------------------------------------------------ meta
    help: str = ""
    output_transaction: bool = False
    suppressed_base_arguments: set[str] = set()
    stealth_options: tuple[str, ...] = ()
    missing_args_message: str | None = None

    # Internal flag — set to True when invoked via run_from_argv().
    _called_from_command_line: bool = False

    # ------------------------------------------------------------------ init

    def __init__(
        self,
        stdout=None,
        stderr=None,
        no_color: bool = False,
        force_color: bool = False,
    ):
        if no_color and force_color:
            raise CommandError("'no_color' and 'force_color' can't be used together.")

        self.stdout = OutputWrapper(stdout or sys.stdout)
        self.stderr = OutputWrapper(stderr or sys.stderr)

        if no_color:
            self.style: Style = no_style()
        else:
            self.style = color_style(force_color=force_color)
            self.stderr.style_func = self.style.ERROR

    # ------------------------------------------------------------------ version

    def get_version(self) -> str:
        """
        Return the version string for this command.

        Override in subclasses to expose your own application version via
        the ``--version`` flag.
        """
        try:
            import importlib.metadata

            # Try to find the package that defines this command's module.
            pkg = self.__module__.split(".")[0]
            return importlib.metadata.version(pkg)
        except Exception:
            return "unknown"

    # ------------------------------------------------------------------ parser

    def create_parser(self, prog_name: str, subcommand: str, **kwargs: Any) -> CommandParser:
        """
        Create and return the ``CommandParser`` used to parse arguments.
        """
        kwargs.setdefault("formatter_class", CommandHelpFormatter)
        parser = CommandParser(
            prog="%s %s" % (os.path.basename(prog_name), subcommand),
            description=self.help or None,
            missing_args_message=self.missing_args_message,
            called_from_command_line=self._called_from_command_line,
            **kwargs,
        )

        self.add_base_argument(
            parser,
            "--version",
            action="version",
            version=self.get_version(),
            help="Show program's version number and exit.",
        )
        self.add_base_argument(
            parser,
            "-v",
            "--verbosity",
            default=1,
            type=int,
            choices=[0, 1, 2, 3],
            help=("Verbosity level; 0=minimal output, 1=normal output, " "2=verbose output, 3=very verbose output."),
        )
        self.add_base_argument(
            parser,
            "--traceback",
            action="store_true",
            help="Raise on CommandError instead of printing a clean error message.",
        )
        self.add_base_argument(
            parser,
            "--no-color",
            action="store_true",
            help="Disable colorized output.",
        )
        self.add_base_argument(
            parser,
            "--force-color",
            action="store_true",
            help="Force colorized output even when not writing to a TTY.",
        )

        self.add_arguments(parser)
        return parser

    def add_base_argument(self, parser: CommandParser, *args: Any, **kwargs: Any):
        """
        Add a base (common) argument, suppressing its help text if its option
        string is listed in ``suppressed_base_arguments``.
        """
        for arg in args:
            if arg in self.suppressed_base_arguments:
                kwargs["help"] = argparse.SUPPRESS
                break
        parser.add_argument(*args, **kwargs)

    def add_arguments(self, parser: CommandParser):
        """
        Override this method to add command-specific arguments.

        Example::

            def add_arguments(self, parser):
                parser.add_argument("name", type=str)
                parser.add_argument("--dry-run", action="store_true")
        """

    def print_help(self, prog_name: str, subcommand: str):
        """Print the help message for this command."""
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    # ------------------------------------------------------------------ execution

    def run_from_argv(self, argv: list[str]):
        """
        Primary entry point when the command is invoked from the CLI.

        Parses ``argv``, applies ``--no-color`` / ``--force-color`` from the
        environment, then delegates to ``execute()``.  Any ``CommandError``
        is caught here, printed to *stderr*, and the process exits with the
        appropriate return code.  Any other exception propagates (or is
        re-raised when ``--traceback`` is active).
        """
        self._called_from_command_line = True

        # Support two calling conventions:
        #   Single-file: [script.py, ...args]         e.g. python greet.py Alice
        #   Runner/Registry pass pre-sliced argv, so argv[0] is always the prog name.
        prog = argv[0]
        remaining = argv[1:]

        parser = self.create_parser(prog, "")
        options = parser.parse_args(remaining)
        cmd_options = vars(options)
        # Pull out positional args collected under the "args" key (LabelCommand).
        args = cmd_options.pop("args", ())

        try:
            self.execute(*args, **cmd_options)
        except CommandError as e:
            if options.traceback:
                raise
            self.stderr.write("%s: %s" % (e.__class__.__name__, e))
            sys.exit(e.returncode)
        except KeyboardInterrupt:
            self.stderr.write("\nAborted.")
            sys.exit(1)

    def execute(self, *args: Any, **options: Any) -> str | None:
        """
        Try to execute the command, applying color / output options, then
        delegate to ``handle()``.

        If ``handle()`` returns a non-empty string *and* ``output_transaction``
        is ``True``, the returned string is wrapped in ``BEGIN;`` / ``COMMIT;``
        before being written to stdout.
        """
        # Apply color options.
        if options.get("force_color") and options.get("no_color"):
            raise CommandError("The --no-color and --force-color options can't be used together.")
        if options.get("force_color"):
            self.style = color_style(force_color=True)
        elif options.get("no_color"):
            self.style = no_style()
            self.stderr.style_func = None

        # Allow stdout/stderr to be overridden at call time (useful for testing).
        if options.get("stdout"):
            self.stdout = OutputWrapper(options["stdout"])
        if options.get("stderr"):
            self.stderr = OutputWrapper(options["stderr"])

        output = self.handle(*args, **options)

        if output:
            if self.output_transaction:
                output = "BEGIN;\n%s\nCOMMIT;" % output
            self.stdout.write(output)

        return output

    def handle(self, *args: Any, **options: Any) -> str | None:
        """
        The actual logic of the command.  **Subclasses must implement this.**

        May return a string; if so the string is written to stdout (wrapped
        in ``BEGIN;`` / ``COMMIT;`` when ``output_transaction`` is ``True``).
        """
        raise NotImplementedError("Subclasses of BaseCommand must implement a handle() method.")


# ---------------------------------------------------------------------------
# LabelCommand
# ---------------------------------------------------------------------------


class LabelCommand(BaseCommand):
    """
    A command that takes one or more arbitrary string labels on the command
    line and calls ``handle_label()`` once per label.

    Override ``handle_label()`` instead of ``handle()``.
    """

    label: str = "label"
    missing_args_message: str = "Enter at least one %s."

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        if self.missing_args_message == LabelCommand.missing_args_message:
            self.missing_args_message = self.missing_args_message % self.label

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("args", metavar=self.label, nargs="+")

    def handle(self, *labels: str, **options: Any) -> str | None:
        output = []
        for label in labels:
            result = self.handle_label(label, **options)
            if result:
                output.append(result)
        return "\n".join(output) if output else None

    def handle_label(self, label: str, **options: Any) -> str | None:
        """
        Perform the command's actions for a single ``label``.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses of LabelCommand must implement handle_label().")
