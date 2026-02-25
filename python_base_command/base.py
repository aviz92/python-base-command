"""
Base classes for writing CLI commands outside of Django.

Mirrors Django's django.core.management.base as closely as possible,
replacing self.stdout / self.style with self.logger from custom-python-logger.
"""

import argparse
import os
import sys
from argparse import Action, ArgumentParser, HelpFormatter
from collections.abc import Sequence
from importlib.metadata import version
from typing import Any, TextIO

from custom_python_logger import CustomLoggerAdapter, build_logger, get_logger
from python_base_toolkit.utils.path_utils import get_project_path_by_file

from python_base_command.const import CURRENT_DATE_TIME_STR, LOG_FILE, LOG_FORMAT


class CommandError(Exception):
    """
    Exception class indicating a problem while executing a command.

    If raised during command execution it will be caught and logged as an error;
    the process exits with ``returncode`` (default 1).

    When invoked via ``call_command()``, it propagates normally.
    """

    def __init__(self, *args: Any, returncode: int = 1, **kwargs: Any) -> None:
        self.returncode = returncode
        super().__init__(*args, **kwargs)


class CommandParser(ArgumentParser):
    """
    Customized ArgumentParser that raises CommandError instead of calling
    sys.exit() when the command is invoked programmatically.
    """

    def __init__(
        self,
        *,
        missing_args_message: str | None = None,
        called_from_command_line: bool | None = None,
        **kwargs: Any,
    ) -> None:
        self.missing_args_message = missing_args_message
        self.called_from_command_line = called_from_command_line
        super().__init__(**kwargs)

    def parse_args(
        self,
        args: Sequence[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ) -> argparse.Namespace:
        if self.missing_args_message and not (args or any(not arg.startswith("-") for arg in (args or []))):
            self.error(self.missing_args_message)
        return super().parse_args(args, namespace)

    def error(self, message: str) -> None:
        if self.called_from_command_line:
            super().error(message)
        else:
            raise CommandError(f"Error: {message}")


class CommandHelpFormatter(HelpFormatter):
    """
    Pushes common base arguments to the bottom of --help output so that
    command-specific arguments appear first.
    """

    show_last: set[str] = {
        "--version",
        "--verbosity",
        "--traceback",
        "--no-color",
        "--force-color",
    }

    def _reordered_actions(self, actions: list[Action]) -> list[Action]:
        return sorted(
            actions,
            key=lambda a: bool(set(a.option_strings) & self.show_last),
        )

    def add_usage(
        self,
        usage: str | None,
        actions: list[Action],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().add_usage(usage, self._reordered_actions(actions), *args, **kwargs)

    def add_arguments(self, actions: list[Action]) -> None:
        super().add_arguments(self._reordered_actions(actions))


class BaseCommand:
    """
    The base class from which all commands derive.

    Instead of Django's self.stdout / self.style, this class exposes
    self.logger — a CustomLoggerAdapter from custom-python-logger.

    Execution flow
    --------------
    1. run_from_argv() parses sys.argv and calls execute().
    2. execute() calls handle() with the parsed options.
    3. Any CommandError raised in handle() is caught, logged, and the
       process exits with the error's returncode.

    Attributes
    ----------
    help : str
        Short description printed in --help output.
    version : str
        Version string exposed via --version. Set this per command.
    output_transaction : bool
        If True, wrap any string returned by handle() with BEGIN; / COMMIT;.
    suppressed_base_arguments : set[str]
        Option strings whose help text should be suppressed.
    stealth_options : tuple[str, ...]
        Options used by the command but not declared via add_arguments().
    missing_args_message : str | None
        Custom error message when required positional arguments are missing.
    """

    help: str = ""
    version: str = "unknown"
    output_transaction: bool = False
    suppressed_base_arguments: set[str] = set()
    stealth_options: tuple[str, ...] = ()
    missing_args_message: str | None = None

    _called_from_command_line: bool = False

    def __init__(
        self,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
    ) -> None:
        _ = stdout, stderr  # API compatibility with call_command(stdout=..., stderr=...)
        self.logger: CustomLoggerAdapter = get_logger(name=self.__class__.__module__.split(".", maxsplit=1)[0])

        build_logger(
            project_name=os.getenv(
                "PYTHON_BASE_COMMAND_PROJECT_NAME", f"{self.__class__.__name__}__{CURRENT_DATE_TIME_STR}"
            ),
            log_format=LOG_FORMAT,
            log_file=LOG_FILE,
        )

    def set_project_version(self, project_name: str | None = None) -> None:
        if not project_name:
            try:
                project_path = get_project_path_by_file()
                project_name = project_path.name
            except Exception:
                self.logger.warning("Project name not provided and could not be inferred from file markers.")
        self.version = version(project_name) if project_name else self.version

    def create_parser(self, prog_name: str, subcommand: str, **kwargs: Any) -> CommandParser:
        """Create and return the CommandParser used to parse arguments."""
        kwargs.setdefault("formatter_class", CommandHelpFormatter)
        parser = CommandParser(
            prog=f"{os.path.basename(prog_name)} {subcommand}",
            description=self.help or None,
            missing_args_message=self.missing_args_message,
            called_from_command_line=self._called_from_command_line,
            **kwargs,
        )

        self.add_base_argument(
            parser,
            "--version",
            action="version",
            version=self.version,
            help="Show program's version number and exit.",
        )
        self.add_base_argument(
            parser,
            "-v",
            "--verbosity",
            default=1,
            type=int,
            choices=[0, 1, 2, 3],
            help="Verbosity level; 0=minimal, 1=normal, 2=verbose, 3=very verbose.",
        )
        self.add_base_argument(
            parser,
            "--traceback",
            action="store_true",
            help="Raise on CommandError instead of logging cleanly.",
        )

        self.add_arguments(parser)
        return parser

    def add_base_argument(self, parser: CommandParser, *args: Any, **kwargs: Any) -> None:
        """Add a base argument, suppressing help if in suppressed_base_arguments."""
        for arg in args:
            if arg in self.suppressed_base_arguments:
                kwargs["help"] = argparse.SUPPRESS
                break
        parser.add_argument(*args, **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        """Override to add command-specific arguments."""

    def print_help(self, prog_name: str, subcommand: str) -> None:
        """Print the help message for this command."""
        parser = self.create_parser(prog_name, subcommand)
        parser.print_help()

    def run_from_argv(self, argv: list[str]) -> None:
        """
        Primary entry point when the command is invoked from the CLI.

        argv[0] = prog name, argv[1:] = arguments (no subcommand slot).
        """
        self._called_from_command_line = True

        prog = argv[0]
        remaining = argv[1:]

        parser = self.create_parser(prog, "")
        options = parser.parse_args(remaining)
        cmd_options = vars(options)
        cmd_options.pop("args", ())

        try:
            self.execute(**cmd_options)
        except CommandError as e:
            if options.traceback:
                raise
            self.logger.error(f"{e.__class__.__name__}: {e}")
            sys.exit(e.returncode)
        except KeyboardInterrupt:
            self.logger.warning("Aborted.")
            sys.exit(1)

    def execute(self, **kwargs: Any) -> str | None:
        """
        Try to execute the command, then delegate to handle().
        If handle() returns a string and output_transaction is True,
        wraps it in BEGIN; / COMMIT;.
        """
        if output := self.handle(**kwargs):
            if self.output_transaction:
                output = f"BEGIN;\n{output}\nCOMMIT;"
            self.logger.info(output)

        return output

    def handle(self, **kwargs: Any) -> str | None:
        """
        The actual logic of the command. Subclasses must implement this.

        Use self.logger.info() / .warning() / .error() / .step() etc.
        May return a string (used with output_transaction).
        """
        raise NotImplementedError("Subclasses of BaseCommand must implement a handle() method.")


class LabelCommand(BaseCommand):
    """
    A command that accepts one or more string labels and calls
    handle_label() once per label. Override handle_label() instead of handle().
    """

    label: str = "label"
    missing_args_message: str = "Enter at least one %s."

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.missing_args_message == LabelCommand.missing_args_message:
            self.missing_args_message = self.missing_args_message % self.label

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("args", metavar=self.label, nargs="+")

    def handle(self, *labels: str, **kwargs: Any) -> str | None:
        output = []
        for label in labels:
            if result := self.handle_label(label, **kwargs):
                output.append(result)
        return "\n".join(output) if output else None

    def handle_label(self, label: str, **kwargs: Any) -> str | None:
        """Perform the command's actions for a single label. Subclasses must implement this."""
        raise NotImplementedError("Subclasses of LabelCommand must implement handle_label().")
