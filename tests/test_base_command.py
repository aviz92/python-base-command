"""
Tests for base-command.

Run with: python -m pytest tests/ -v
"""

import sys
from typing import Any

import pytest

from python_base_command import (
    BaseCommand,
    CommandError,
    CommandRegistry,
    LabelCommand,
    call_command,
)
from python_base_command.base import CommandParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_command(
    handle_fn: Any = None,
    add_args_fn: Any = None,
    **class_attrs: Any,
) -> type[BaseCommand]:
    """Dynamically create a BaseCommand subclass for testing."""

    def _handle(self: BaseCommand, *args: Any, **options: Any) -> Any:
        if handle_fn:
            return handle_fn(self, *args, **options)
        return None

    attrs: dict[str, Any] = {"handle": _handle, **class_attrs}
    if add_args_fn:
        attrs["add_arguments"] = add_args_fn

    return type("TestCommand", (BaseCommand,), attrs)


# ---------------------------------------------------------------------------
# CommandError
# ---------------------------------------------------------------------------


class TestCommandError:
    def test_default_returncode(self) -> None:
        assert CommandError("oops").returncode == 1

    def test_custom_returncode(self) -> None:
        assert CommandError("oops", returncode=42).returncode == 42

    def test_is_exception(self) -> None:
        assert isinstance(CommandError("x"), Exception)


# ---------------------------------------------------------------------------
# BaseCommand — logger
# ---------------------------------------------------------------------------


class TestBaseCommandLogger:
    def test_has_logger(self) -> None:
        cmd = make_command()()
        assert hasattr(cmd, "logger")

    def test_logger_has_info(self) -> None:
        cmd = make_command()()
        assert callable(cmd.logger.info)

    def test_logger_has_warning(self) -> None:
        cmd = make_command()()
        assert callable(cmd.logger.warning)

    def test_logger_has_error(self) -> None:
        cmd = make_command()()
        assert callable(cmd.logger.error)

    def test_logger_has_step(self) -> None:
        cmd = make_command()()
        assert callable(cmd.logger.step)

    def test_logger_has_debug(self) -> None:
        cmd = make_command()()
        assert callable(cmd.logger.debug)


# ---------------------------------------------------------------------------
# BaseCommand — argument parsing
# ---------------------------------------------------------------------------


class TestBaseCommandParser:
    def test_has_version_flag(self) -> None:
        parser = make_command()().create_parser("prog", "test")
        assert "--version" in parser.format_help()

    def test_has_verbosity_flag(self) -> None:
        parser = make_command()().create_parser("prog", "test")
        assert "--verbosity" in parser.format_help()

    def test_has_traceback_flag(self) -> None:
        parser = make_command()().create_parser("prog", "test")
        assert "--traceback" in parser.format_help()

    def test_custom_argument(self) -> None:
        def add_args(self: BaseCommand, parser: CommandParser) -> None:
            parser.add_argument("name")

        cmd_class = make_command(add_args_fn=add_args)
        parser = cmd_class().create_parser("prog", "test")
        args = parser.parse_args(["Alice"])
        assert args.name == "Alice"

    def test_suppressed_base_argument(self) -> None:
        cmd_class = make_command(suppressed_base_arguments={"--traceback"})
        parser = cmd_class().create_parser("prog", "test")
        assert "traceback" not in parser.format_help()


# ---------------------------------------------------------------------------
# BaseCommand — execute / handle
# ---------------------------------------------------------------------------


class TestBaseCommandExecute:
    def test_handle_called(self) -> None:
        called = []

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            called.append(options["verbosity"])

        cmd_class = make_command(handle_fn=handle)
        call_command(cmd_class)
        assert called == [1]

    def test_handle_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            call_command(BaseCommand)

    def test_output_transaction_wraps_output(self) -> None:
        messages = []

        class TxCmd(BaseCommand):
            output_transaction = True

            def handle(self, *args: Any, **options: Any) -> str:
                return "SELECT 1;"

        cmd = TxCmd()
        cmd.logger.info = lambda msg, *a, **kw: messages.append(msg)

        cmd.execute()
        assert len(messages) == 1
        assert "BEGIN;" in messages[0]
        assert "COMMIT;" in messages[0]
        assert "SELECT 1;" in messages[0]

    def test_command_error_propagates_in_call_command(self) -> None:
        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            raise CommandError("boom")

        cmd_class = make_command(handle_fn=handle)
        with pytest.raises(CommandError, match="boom"):
            call_command(cmd_class)

    def test_verbosity_passed(self) -> None:
        received = []

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            received.append(options["verbosity"])

        cmd_class = make_command(handle_fn=handle)
        call_command(cmd_class, verbosity=3)
        assert received == [3]


# ---------------------------------------------------------------------------
# BaseCommand — run_from_argv
# ---------------------------------------------------------------------------


class TestRunFromArgv:
    def test_exits_on_command_error(self) -> None:
        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            raise CommandError("fail", returncode=2)

        cmd_class = make_command(handle_fn=handle)
        with pytest.raises(SystemExit) as exc_info:
            cmd_class().run_from_argv(["prog"])
        assert exc_info.value.code == 2

    def test_traceback_reraises(self) -> None:
        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            raise CommandError("reraise me")

        cmd_class = make_command(handle_fn=handle)
        with pytest.raises(CommandError):
            cmd_class().run_from_argv(["prog", "--traceback"])

    def test_keyboard_interrupt_exits_1(self) -> None:
        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            raise KeyboardInterrupt

        cmd_class = make_command(handle_fn=handle)
        with pytest.raises(SystemExit) as exc_info:
            cmd_class().run_from_argv(["prog"])
        assert exc_info.value.code == 1

    def test_positional_arg_parsed_correctly(self) -> None:
        received = []

        def add_args(self: BaseCommand, parser: CommandParser) -> None:
            parser.add_argument("name")

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            received.append(options["name"])

        cmd_class = make_command(handle_fn=handle, add_args_fn=add_args)
        cmd_class().run_from_argv(["prog", "Alice"])
        assert received == ["Alice"]

    def test_flag_parsed_correctly(self) -> None:
        received = []

        def add_args(self: BaseCommand, parser: CommandParser) -> None:
            parser.add_argument("--shout", action="store_true")

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            received.append(options["shout"])

        cmd_class = make_command(handle_fn=handle, add_args_fn=add_args)
        cmd_class().run_from_argv(["prog", "--shout"])
        assert received == [True]


# ---------------------------------------------------------------------------
# LabelCommand
# ---------------------------------------------------------------------------


class TestLabelCommand:
    def test_handle_label_called_for_each_label(self) -> None:
        seen = []

        class Cmd(LabelCommand):
            def handle_label(self, label: str, **options: Any) -> None:
                seen.append(label)

        Cmd().run_from_argv(["prog", "foo", "bar"])
        assert seen == ["foo", "bar"]

    def test_handle_label_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            call_command(LabelCommand, "x")

    def test_output_joined(self) -> None:
        class Cmd(LabelCommand):
            def handle_label(self, label: str, **options: Any) -> str:
                return label.upper()

        result = call_command(Cmd, "a", "b")
        assert result == "A\nB"


# ---------------------------------------------------------------------------
# CommandRegistry
# ---------------------------------------------------------------------------


class TestCommandRegistry:
    def test_register_and_get(self) -> None:
        reg = CommandRegistry()

        @reg.register("hello")
        class HelloCmd(BaseCommand):
            def handle(self, *args: Any, **options: Any) -> None:
                pass

        assert reg.get("hello") is HelloCmd

    def test_list_commands(self) -> None:
        reg = CommandRegistry()

        @reg.register("z_cmd")
        class _Z(BaseCommand):
            def handle(self, *args: Any, **options: Any) -> None:
                pass

        @reg.register("a_cmd")
        class _A(BaseCommand):
            def handle(self, *args: Any, **options: Any) -> None:
                pass

        assert reg.list_commands() == ["a_cmd", "z_cmd"]

    def test_unknown_command_exits(self) -> None:
        reg = CommandRegistry()
        with pytest.raises(SystemExit) as exc_info:
            reg.run(["prog", "nonexistent"])
        assert exc_info.value.code == 1

    def test_help_exits_0(self) -> None:
        reg = CommandRegistry()
        with pytest.raises(SystemExit) as exc_info:
            reg.run(["prog", "--help"])
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# call_command
# ---------------------------------------------------------------------------


class TestCallCommand:
    def test_accepts_class(self) -> None:
        class Cmd(BaseCommand):
            def handle(self, *args: Any, **options: Any) -> str:
                return "ok"

        assert call_command(Cmd) == "ok"

    def test_accepts_instance(self) -> None:
        class Cmd(BaseCommand):
            def handle(self, *args: Any, **options: Any) -> str:
                return "ok"

        assert call_command(Cmd()) == "ok"
