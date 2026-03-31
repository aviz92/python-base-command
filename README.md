![PyPI version](https://img.shields.io/pypi/v/python-base-command)
![Python](https://img.shields.io/badge/python->=3.12-blue)
![Development Status](https://img.shields.io/badge/status-stable-green)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
![PyPI](https://img.shields.io/pypi/dm/python-base-command)
![License](https://img.shields.io/pypi/l/python-base-command)

---

# python-base-command
A Django-style `BaseCommand` framework for **standalone** Python CLI tools — no Django required.

If you've ever written a Django management command and wished you could use the same clean pattern anywhere in Python, this is for you.

---

## 🚀 Features

- ✅ **Django-style API** — `handle()`, `add_arguments()`, `CommandError`, `LabelCommand` — the same pattern you already know
- ✅ **Built-in logging** — `self.logger` powered by [`custom-python-logger`](https://pypi.org/project/custom-python-logger/), with colored output and custom levels (`step`, `exception`)
- ✅ **Auto-discovery** — drop `.py` files into a `commands/` folder and they're automatically available, just like Django's `manage.py`
- ✅ **Manual registry** — register commands explicitly with the `@registry.register()` decorator
- ✅ **Built-in flags** — every command gets `--version`, `--verbosity`, `--traceback` for free
- ✅ **`call_command()`** — invoke commands programmatically, perfect for testing
- ✅ **`output_transaction`** — wrap SQL output in `BEGIN;` / `COMMIT;` automatically
- ✅ **Zero Django dependency** — works in any Python project
- ✅ **Python 3.12+**

---

## 📦 Installation

```bash
pip install python-base-command
```

Dependencies: [`custom-python-logger==2.0.13`](https://pypi.org/project/custom-python-logger/) — installed automatically.

---

## ⚡ Quick Start

Add commands to a `commands/` folder:

```
myapp/
├── pyproject.toml
└── commands/
    ├── __init__.py
    └── greet.py
```

```python
# commands/greet.py
from python_base_command import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Greet a user by name"
    version = "1.0.0"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str, help="Name to greet")
        parser.add_argument("--shout", action="store_true", help="Print in uppercase")

    def handle(self, **kwargs):
        name = kwargs["name"].strip()
        if not name:
            raise CommandError("Name cannot be empty.")

        msg = f"Hello, {name}!"
        if kwargs["shout"]:
            msg = msg.upper()

        self.logger.info(msg)
```

### Packaging as a CLI tool (recommended)

Register your entry point in `pyproject.toml` — this is the preferred way to expose a CLI tool when distributing your project as a package.

**Option A — Single command** (one `BaseCommand` subclass, no `Runner`):

```toml
# pyproject.toml
[project.scripts]
myapp = "myapp.commands.greet:main"
```

```python
# myapp/commands/greet.py
import sys
from python_base_command import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Greet a user by name"
    version = "1.0.0"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str, help="Name to greet")
        parser.add_argument("--shout", action="store_true", help="Print in uppercase")

    def handle(self, **kwargs):
        name = kwargs["name"].strip()
        if not name:
            raise CommandError("Name cannot be empty.")
        msg = f"Hello, {name}!"
        if kwargs["shout"]:
            msg = msg.upper()
        self.logger.info(msg)


def main():
    Command().run_from_argv(sys.argv)
```

**Option B — Multiple commands** (auto-discovery via `Runner`):

```toml
# pyproject.toml
[project.scripts]
myapp = "myapp.__main__:main"
```

```python
# myapp/__main__.py
import sys
from python_base_command import Runner

def main():
    Runner(commands_dir="myapp/commands").run(sys.argv)
```

Once installed (`pip install myapp` or `uv add myapp`), the command is available globally:

```bash
myapp --help
myapp greet Alice
myapp greet Alice --shout
myapp greet --version
myapp greet --verbosity 2
```

### Local development (without installing)

For local development only, you can use a `cli.py` script as a quick entry point — the equivalent of Django's `manage.py`:

```python
# cli.py  ← dev only, do not distribute
import sys
from python_base_command import Runner

Runner(commands_dir="commands").run(sys.argv)
```

```bash
python3 cli.py --help
python3 cli.py greet Alice
```

> **Note:** `cli.py` is a development convenience only. For distributed packages, always use `[project.scripts]` in `pyproject.toml`.

---

## 📋 Manual Registry

Register commands explicitly using the `@registry.register()` decorator — useful when you want multiple commands in a single file.

The registry style works in two ways:

**Standalone** — run the registry directly as a script:

```python
# my_commands.py
from python_base_command import BaseCommand, CommandError, CommandRegistry

registry = CommandRegistry()


@registry.register("greet")
class GreetCommand(BaseCommand):
    help = "Greet a user"
    version = "2.0.0"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)

    def handle(self, **kwargs):
        self.logger.info(f"Hello, {kwargs['name']}!")


@registry.register("export")
class ExportCommand(BaseCommand):
    help = "Export data"
    version = "3.0.0"

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=["csv", "json"], default="csv")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, **kwargs):
        if kwargs["dry_run"]:
            self.logger.warning("Dry run — no files written.")
            return
        self.logger.info(f"Exported as {kwargs['format']}.")


if __name__ == "__main__":
    registry.run()
```

```bash
python3 my_commands.py greet Alice
python3 my_commands.py export --format json
python3 my_commands.py export --dry-run
```

**Auto-discovered** — drop the registry file into your `commands/` folder and `Runner` will discover it automatically alongside any classic `Command` files:

```
myapp/
├── cli.py
└── commands/
    ├── __init__.py
    ├── greet.py       ← classic Command class
    └── reg_cmd.py     ← CommandRegistry with multiple commands
```

```bash
python3 cli.py --help          # shows commands from both files
python3 cli.py greet Alice
python3 cli.py export --format json
```

---

## 🧪 Testing with `call_command`

Invoke commands programmatically — ideal for unit tests.

```python
from python_base_command import call_command, CommandError
import pytest

from commands.greet import Command as GreetCommand


def test_greet():
    result = call_command(GreetCommand, name="Alice")
    assert result is None  # handle() logs, doesn't return


def test_greet_empty_name():
    with pytest.raises(CommandError, match="cannot be empty"):
        call_command(GreetCommand, name="")
```

`CommandError` propagates normally when using `call_command()` — it is only caught and logged when invoked from the CLI.

---

## 📖 API Reference

### `BaseCommand`

Base class for all commands. Inherit from it and implement `handle()`.

**Class attributes**

| Attribute | Type | Default | Description |
|---|---|---|---|
| `help` | `str` | `""` | Description shown in `--help` |
| `version` | `str` | `"unknown"` | Version string exposed via `--version`. Set this per command. |
| `output_transaction` | `bool` | `False` | Wrap `handle()` return value in `BEGIN;` / `COMMIT;` |
| `suppressed_base_arguments` | `set[str]` | `set()` | Base flags to hide from `--help` |
| `stealth_options` | `tuple[str]` | `()` | Options used but not declared via `add_arguments()` |
| `missing_args_message` | `str \| None` | `None` | Custom message when required positional args are missing |

**Methods to override**

| Method | Required | Description |
|---|---|---|
| `handle(**kwargs)` | ✅ | Command logic. May return a string. |
| `add_arguments(parser)` | ❌ | Add command-specific arguments to the parser. |

**`self.logger`**

A `CustomLoggerAdapter` from `custom-python-logger`, available inside every command:

```python
self.logger.debug("...")
self.logger.info("...")
self.logger.step("...")        # custom level for process steps
self.logger.warning("...")
self.logger.error("...")
self.logger.critical("...")
self.logger.exception("...")   # logs with full traceback
```

**Built-in flags** — available on every command automatically:

| Flag | Description |
|---|---|
| `--version` | Print the version and exit |
| `-v` / `--verbosity` | Verbosity level: 0=minimal, 1=normal, 2=verbose, 3=very verbose (default: 1) |
| `--traceback` | Re-raise `CommandError` with full traceback instead of logging cleanly |

---

### `CommandError`

Raise this to signal that something went wrong. When raised inside `handle()` during CLI invocation, it is caught, logged as an error, and the process exits with `returncode`. When invoked via `call_command()`, it propagates normally.

```python
raise CommandError("Something went wrong.")
raise CommandError("Fatal error.", returncode=2)
```

---

### `LabelCommand`

For commands that accept one or more arbitrary string labels. Override `handle_label()` instead of `handle()`.

```python
from python_base_command import LabelCommand, CommandError


class Command(LabelCommand):
    label = "filepath"
    help = "Process one or more files"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--strict", action="store_true")

    def handle_label(self, label, **kwargs):
        if not label.endswith((".txt", ".csv", ".json")):
            msg = f"Unsupported file type: '{label}'"
            if kwargs["strict"]:
                raise CommandError(msg)
            self.logger.warning(f"Skipping — {msg}")
            return None
        self.logger.info(f"Processed: {label}")
        return f"ok:{label}"
```

```bash
python3 cli.py process report.csv notes.txt image.png
python3 cli.py process report.csv notes.txt image.png --strict
```

---

### `Runner`

Auto-discovers commands from a directory. Two conventions are supported:

1. **Classic** — a `.py` file that defines a class named `Command` subclassing `BaseCommand`. The command name is the file stem.
2. **Registry** — a `.py` file that defines one or more `CommandRegistry` instances. Every command registered on those instances is merged in automatically; command names come from the registry, not the file name.

Files whose names start with `_` are ignored.

```python
from python_base_command import Runner

Runner(commands_dir="commands").run()
```

---

### `CommandRegistry`

Manually register commands using a decorator or programmatically.

```python
from python_base_command import BaseCommand, CommandRegistry

registry = CommandRegistry()


@registry.register("greet")
class GreetCommand(BaseCommand): ...


registry.add("export", ExportCommand)  # programmatic alternative

registry.run()                                      # uses sys.argv
registry.run(["myapp", "greet", "Alice"])           # explicit argv
```

---

### `call_command`

Invoke a command from Python code. Accepts either a class or an instance.

```python
from python_base_command import call_command

call_command(GreetCommand, name="Alice")
call_command(GreetCommand, name="Alice", verbosity=0)
call_command(GreetCommand())
```

---

## 🔄 Comparison with Django

| Feature | Django `BaseCommand` | `python-base-command` |
|---|---|---|
| `handle()` / `add_arguments()` | ✅ | ✅ |
| `self.logger` (via custom-python-logger) | ❌ | ✅ |
| `self.stdout` / `self.style` | ✅ | ❌ replaced by `self.logger` |
| `--version` / `--verbosity` / `--traceback` | ✅ | ✅ |
| `CommandError` with `returncode` | ✅ | ✅ |
| `LabelCommand` | ✅ | ✅ |
| `call_command()` | ✅ | ✅ |
| `output_transaction` | ✅ | ✅ |
| Auto-discovery from folder | ✅ | ✅ |
| Manual registry | ❌ | ✅ |
| Django dependency | ✅ required | ❌ none |

---

## 🤝 Contributing
If you have a helpful tool, pattern, or improvement to suggest:
Fork the repo <br>
Create a new branch <br>
Submit a pull request <br>
I welcome additions that promote clean, productive, and maintainable development. <br>

---

## 🙏 Thanks
Thanks for exploring this repository! <br>
Happy coding! <br>
