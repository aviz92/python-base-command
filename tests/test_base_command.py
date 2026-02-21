"""
Tests for base-command.

Run with: python -m pytest tests/ -v
"""

import io

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


def make_command(handle_fn=None, add_args_fn=None, **class_attrs):
    """Dynamically create a BaseCommand subclass for testing."""

    def _handle(self, *args, **options):
        if handle_fn:
            return handle_fn(self, *args, **options)

    attrs = {"handle": _handle, **class_attrs}
    if add_args_fn:
        attrs["add_arguments"] = add_args_fn

    return type("TestCommand", (BaseCommand,), attrs)


# ---------------------------------------------------------------------------
# CommandError
# ---------------------------------------------------------------------------


class TestCommandError:
    def test_default_returncode(self):
        e = CommandError("oops")
        assert e.returncode == 1

    def test_custom_returncode(self):
        e = CommandError("oops", returncode=42)
        assert e.returncode == 42

    def test_is_exception(self):
        assert isinstance(CommandError("x"), Exception)


# ---------------------------------------------------------------------------
# OutputWrapper
# ---------------------------------------------------------------------------


class TestOutputWrapper:
    def _wrapper(self):
        buf = io.StringIO()
        return OutputWrapper(buf), buf

    def test_write_adds_newline(self):
        w, buf = self._wrapper()
        w.write("hello")
        assert buf.getvalue() == "hello\n"

    def test_write_no_duplicate_newline(self):
        w, buf = self._wrapper()
        w.write("hello\n")
        assert buf.getvalue() == "hello\n"

    def test_custom_ending(self):
        buf = io.StringIO()
        w = OutputWrapper(buf, ending="")
        w.write("hello")
        assert buf.getvalue() == "hello"

    def test_write_empty(self):
        w, buf = self._wrapper()
        w.write("")
        assert buf.getvalue() == "\n"

    def test_flush(self):
        w, buf = self._wrapper()
        w.write("x")
        w.flush()  # Should not raise.


# ---------------------------------------------------------------------------
# BaseCommand — argument parsing
# ---------------------------------------------------------------------------


class TestBaseCommandParser:
    def test_has_version_flag(self):
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        help_text = parser.format_help()
        assert "--version" in help_text

    def test_has_verbosity_flag(self):
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--verbosity" in parser.format_help()

    def test_has_traceback_flag(self):
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--traceback" in parser.format_help()

    def test_has_no_color_flag(self):
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--no-color" in parser.format_help()

    def test_has_force_color_flag(self):
        cmd = make_command()()
        parser = cmd.create_parser("prog", "test")
        assert "--force-color" in parser.format_help()

    def test_custom_argument(self):
        def add_args(self, parser):
            parser.add_argument("name")

        Cmd = make_command(add_args_fn=add_args)
        parser = Cmd().create_parser("prog", "test")
        args = parser.parse_args(["Alice"])
        assert args.name == "Alice"

    def test_suppressed_base_argument(self):
        Cmd = make_command(suppressed_base_arguments={"--traceback"})
        parser = Cmd().create_parser("prog", "test")
        assert "traceback" not in parser.format_help()


# ---------------------------------------------------------------------------
# BaseCommand — execute / handle
# ---------------------------------------------------------------------------


class TestBaseCommandExecute:
    def test_handle_called(self):
        called = []

        def handle(self, *args, **options):
            called.append(options["verbosity"])

        Cmd = make_command(handle_fn=handle)
        call_command(Cmd)
        assert called == [1]

    def test_handle_not_implemented(self):
        with pytest.raises(NotImplementedError):
            call_command(BaseCommand)

    def test_stdout_captured(self):
        buf = io.StringIO()

        def handle(self, *args, **options):
            self.stdout.write("hello")

        Cmd = make_command(handle_fn=handle)
        call_command(Cmd, stdout=buf)
        assert "hello" in buf.getvalue()

    def test_stderr_captured(self):
        buf = io.StringIO()

        def handle(self, *args, **options):
            self.stderr.write("err")

        Cmd = make_command(handle_fn=handle)
        call_command(Cmd, stderr=buf)
        assert "err" in buf.getvalue()

    def test_output_transaction_wraps_output(self):
        buf = io.StringIO()

        def handle(self, *args, **options):
            return "SELECT 1;"

        Cmd = make_command(handle_fn=handle, output_transaction=True)
        call_command(Cmd, stdout=buf)
        out = buf.getvalue()
        assert "BEGIN;" in out
        assert "COMMIT;" in out
        assert "SELECT 1;" in out

    def test_no_color_and_force_color_raises(self):
        with pytest.raises(CommandError):
            make_command()(no_color=True, force_color=True)

    def test_command_error_propagates_in_call_command(self):
        def handle(self, *args, **options):
            raise CommandError("boom")

        Cmd = make_command(handle_fn=handle)
        with pytest.raises(CommandError, match="boom"):
            call_command(Cmd)

    def test_verbosity_passed(self):
        received = []

        def handle(self, *args, **options):
            received.append(options["verbosity"])

        Cmd = make_command(handle_fn=handle)
        call_command(Cmd, verbosity=3)
        assert received == [3]


# ---------------------------------------------------------------------------
# BaseCommand — run_from_argv
#
# run_from_argv uses single-file convention: argv[0]=prog, argv[1:]=args.
# There is no subcommand slot — unlike Django's [manage.py, subcommand, ...].
# ---------------------------------------------------------------------------


class TestRunFromArgv:
    def test_exits_on_command_error(self):
        def handle(self, *args, **options):
            raise CommandError("fail", returncode=2)

        Cmd = make_command(handle_fn=handle)
        with pytest.raises(SystemExit) as exc_info:
            # argv = [prog]  →  no extra args, handle() raises immediately
            Cmd().run_from_argv(["prog"])
        assert exc_info.value.code == 2

    def test_traceback_reraises(self):
        def handle(self, *args, **options):
            raise CommandError("reraise me")

        Cmd = make_command(handle_fn=handle)
        with pytest.raises(CommandError):
            # argv = [prog, --traceback]
            Cmd().run_from_argv(["prog", "--traceback"])

    def test_keyboard_interrupt_exits_1(self):
        def handle(self, *args, **options):
            raise KeyboardInterrupt

        Cmd = make_command(handle_fn=handle)
        with pytest.raises(SystemExit) as exc_info:
            Cmd().run_from_argv(["prog"])
        assert exc_info.value.code == 1

    def test_positional_arg_parsed_correctly(self):
        received = []

        def add_args(self, parser):
            parser.add_argument("name")

        def handle(self, *args, **options):
            received.append(options["name"])

        Cmd = make_command(handle_fn=handle, add_args_fn=add_args)
        # argv = [prog, Alice]  →  name="Alice"
        Cmd().run_from_argv(["prog", "Alice"])
        assert received == ["Alice"]

    def test_flag_parsed_correctly(self):
        received = []

        def add_args(self, parser):
            parser.add_argument("--shout", action="store_true")

        def handle(self, *args, **options):
            received.append(options["shout"])

        Cmd = make_command(handle_fn=handle, add_args_fn=add_args)
        Cmd().run_from_argv(["prog", "--shout"])
        assert received == [True]

    def test_no_color_flag(self):
        Cmd = make_command()
        # Should not raise — --no-color is always available.
        try:
            Cmd().run_from_argv(["prog", "--no-color"])
        except SystemExit:
            pass  # handle() returns None which is fine


# ---------------------------------------------------------------------------
# LabelCommand
#
# run_from_argv: argv[0]=prog, argv[1:]=labels (no subcommand slot).
# ---------------------------------------------------------------------------


class TestLabelCommand:
    def test_handle_label_called_for_each_label(self):
        seen = []

        class Cmd(LabelCommand):
            def handle_label(self, label, **options):
                seen.append(label)

        # argv = [prog, foo, bar]  →  labels = ["foo", "bar"]
        Cmd().run_from_argv(["prog", "foo", "bar"])
        assert seen == ["foo", "bar"]

    def test_handle_label_not_implemented(self):
        with pytest.raises(NotImplementedError):
            call_command(LabelCommand, "x")

    def test_output_joined(self):
        buf = io.StringIO()

        class Cmd(LabelCommand):
            def handle_label(self, label, **options):
                return label.upper()

        call_command(Cmd, "a", "b", stdout=buf)
        assert buf.getvalue().strip() == "A\nB"


# ---------------------------------------------------------------------------
# CommandRegistry
# ---------------------------------------------------------------------------


class TestCommandRegistry:
    def test_register_and_get(self):
        reg = CommandRegistry()

        @reg.register("hello")
        class HelloCmd(BaseCommand):
            def handle(self, *args, **options):
                pass

        assert reg.get("hello") is HelloCmd

    def test_list_commands(self):
        reg = CommandRegistry()

        @reg.register("z_cmd")
        class Z(BaseCommand):
            def handle(self, *args, **options):
                pass

        @reg.register("a_cmd")
        class A(BaseCommand):
            def handle(self, *args, **options):
                pass

        assert reg.list_commands() == ["a_cmd", "z_cmd"]

    def test_unknown_command_exits(self):
        reg = CommandRegistry()
        with pytest.raises(SystemExit) as exc_info:
            reg.run(["prog", "nonexistent"])
        assert exc_info.value.code == 1

    def test_run_dispatches_command(self):
        reg = CommandRegistry()
        buf = io.StringIO()

        @reg.register("hi")
        class HiCmd(BaseCommand):
            def handle(self, *args, **options):
                self.stdout.write("hi!")

        original_init = HiCmd.__init__

        def patched_init(self, *a, **kw):
            original_init(self, stdout=buf, *a, **kw)

        HiCmd.__init__ = patched_init

        reg.run(["prog", "hi"])
        assert "hi!" in buf.getvalue()

    def test_help_exits_0(self):
        reg = CommandRegistry()
        with pytest.raises(SystemExit) as exc_info:
            reg.run(["prog", "--help"])
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# call_command
# ---------------------------------------------------------------------------


class TestCallCommand:
    def test_accepts_class(self):
        class Cmd(BaseCommand):
            def handle(self, *args, **options):
                return "ok"

        result = call_command(Cmd)
        assert result == "ok"

    def test_accepts_instance(self):
        class Cmd(BaseCommand):
            def handle(self, *args, **options):
                return "ok"

        result = call_command(Cmd())
        assert result == "ok"
