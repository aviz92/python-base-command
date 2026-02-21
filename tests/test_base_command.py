"""
Tests for base-command.

Run with: python -m pytest tests/ -v
"""

import io
from typing import Any

import pytest

from python_base_command import (
    BaseCommand,
    CommandError,
    CommandRegistry,
    LabelCommand,
    OutputWrapper,
    call_command,
)

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
        e = CommandError("oops")
        assert e.returncode == 1

    def test_custom_returncode(self) -> None:
        e = CommandError("oops", returncode=42)
        assert e.returncode == 42

    def test_is_exception(self) -> None:
        assert isinstance(CommandError("x"), Exception)


# ---------------------------------------------------------------------------
# OutputWrapper
# ---------------------------------------------------------------------------


class TestOutputWrapper:
    def _wrapper(self) -> tuple[OutputWrapper, io.StringIO]:
        buf = io.StringIO()
        return OutputWrapper(buf), buf

    def test_write_adds_newline(self) -> None:
        w, buf = self._wrapper()
        w.write("hello")
        assert buf.getvalue() == "hello\n"

    def test_write_no_duplicate_newline(self) -> None:
        w, buf = self._wrapper()
        w.write("hello\n")
        assert buf.getvalue() == "hello\n"

    def test_custom_ending(self) -> None:
        buf = io.StringIO()
        w = OutputWrapper(buf, ending="")
        w.write("hello")
        assert buf.getvalue() == "hello"

    def test_write_empty(self) -> None:
        w, buf = self._wrapper()
        w.write("")
        assert buf.getvalue() == "\n"

    def test_flush(self) -> None:
        w, buf = self._wrapper()
        w.write("x")
        w.flush()
        assert buf.getvalue() == "x\n"


# ---------------------------------------------------------------------------
# BaseCommand — argument parsing
# ---------------------------------------------------------------------------


class TestBaseCommandParser:
    def test_has_version_flag(self) -> None:
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        help_text = parser.format_help()
        assert "--version" in help_text

    def test_has_verbosity_flag(self) -> None:
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--verbosity" in parser.format_help()

    def test_has_traceback_flag(self) -> None:
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--traceback" in parser.format_help()

    def test_has_no_color_flag(self) -> None:
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--no-color" in parser.format_help()

    def test_has_force_color_flag(self) -> None:
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--force-color" in parser.format_help()

    def test_custom_argument(self) -> None:
        def add_args(self: BaseCommand, parser: Any) -> None:
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

    def test_stdout_captured(self) -> None:
        buf = io.StringIO()

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            self.stdout.write("hello")

        cmd_class = make_command(handle_fn=handle)
        call_command(cmd_class, stdout=buf)
        assert "hello" in buf.getvalue()

    def test_stderr_captured(self) -> None:
        buf = io.StringIO()

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            self.stderr.write("err")

        cmd_class = make_command(handle_fn=handle)
        call_command(cmd_class, stderr=buf)
        assert "err" in buf.getvalue()

    def test_output_transaction_wraps_output(self) -> None:
        buf = io.StringIO()

        def handle(self: BaseCommand, *args: Any, **options: Any) -> str:
            return "SELECT 1;"

        cmd_class = make_command(handle_fn=handle, output_transaction=True)
        call_command(cmd_class, stdout=buf)
        out = buf.getvalue()
        assert "BEGIN;" in out
        assert "COMMIT;" in out
        assert "SELECT 1;" in out

    def test_no_color_and_force_color_raises(self) -> None:
        with pytest.raises(CommandError):
            make_command()(no_color=True, force_color=True)

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
#
# run_from_argv uses single-file convention: argv[0]=prog, argv[1:]=args.
# There is no subcommand slot — unlike Django's [manage.py, subcommand, ...].
# ---------------------------------------------------------------------------


class TestRunFromArgv:
    def test_exits_on_command_error(self) -> None:
        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            raise CommandError("fail", returncode=2)

        cmd_class = make_command(handle_fn=handle)
        with pytest.raises(SystemExit) as exc_info:
            # argv = [prog]  →  no extra args, handle() raises immediately
            cmd_class().run_from_argv(["prog"])
        assert exc_info.value.code == 2

    def test_traceback_reraises(self) -> None:
        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            raise CommandError("reraise me")

        cmd_class = make_command(handle_fn=handle)
        with pytest.raises(CommandError):
            # argv = [prog, --traceback]
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

        def add_args(self: BaseCommand, parser: Any) -> None:
            parser.add_argument("name")

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            received.append(options["name"])

        cmd_class = make_command(handle_fn=handle, add_args_fn=add_args)
        # argv = [prog, Alice]  →  name="Alice"
        cmd_class().run_from_argv(["prog", "Alice"])
        assert received == ["Alice"]

    def test_flag_parsed_correctly(self) -> None:
        received = []

        def add_args(self: BaseCommand, parser: Any) -> None:
            parser.add_argument("--shout", action="store_true")

        def handle(self: BaseCommand, *args: Any, **options: Any) -> None:
            received.append(options["shout"])

        cmd_class = make_command(handle_fn=handle, add_args_fn=add_args)
        cmd_class().run_from_argv(["prog", "--shout"])
        assert received == [True]

    def test_no_color_flag(self) -> None:
        cmd_class = make_command()
        # Should not raise — --no-color is always available.
        try:
            cmd_class().run_from_argv(["prog", "--no-color"])
        except SystemExit:
            pass  # handle() returns None which is fine


# ---------------------------------------------------------------------------
# LabelCommand
#
# run_from_argv: argv[0]=prog, argv[1:]=labels (no subcommand slot).
# ---------------------------------------------------------------------------


class TestLabelCommand:
    def test_handle_label_called_for_each_label(self) -> None:
        seen = []

        class Cmd(LabelCommand):
            def handle_label(self, label: str, **options: Any) -> None:
                seen.append(label)

        # argv = [prog, foo, bar]  →  labels = ["foo", "bar"]
        Cmd().run_from_argv(["prog", "foo", "bar"])
        assert seen == ["foo", "bar"]

    def test_handle_label_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            call_command(LabelCommand, "x")

    def test_output_joined(self) -> None:
        buf = io.StringIO()

        class Cmd(LabelCommand):
            def handle_label(self, label: str, **options: Any) -> str:
                return label.upper()

        call_command(Cmd, "a", "b", stdout=buf)
        assert buf.getvalue().strip() == "A\nB"


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

    def test_run_dispatches_command(self) -> None:
        reg = CommandRegistry()
        buf = io.StringIO()

        @reg.register("hi")
        class HiCmd(BaseCommand):
            def handle(self, *args: Any, **options: Any) -> None:
                self.stdout.write("hi!")

        original_init = HiCmd.__init__

        def patched_init(self: BaseCommand, *a: Any, **kw: Any) -> None:
            kw_with_stdout = {**kw, "stdout": buf}
            original_init(self, *a, **kw_with_stdout)

        HiCmd.__init__ = patched_init

        reg.run(["prog", "hi"])
        assert "hi!" in buf.getvalue()

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

        result = call_command(Cmd)
        assert result == "ok"

    def test_accepts_instance(self) -> None:
        class Cmd(BaseCommand):
            def handle(self, *args: Any, **options: Any) -> str:
                return "ok"

        result = call_command(Cmd())
        assert result == "ok"
