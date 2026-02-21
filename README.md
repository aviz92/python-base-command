# python-base-command

A Django-style `BaseCommand` framework for **standalone** Python CLI tools — no Django required.

If you've ever written a Django management command and wished you could use the same clean pattern in a regular Python project, this is for you.

---

## Installation

```bash
pip install python-base-command
```

---

## Quick Start

### Method 1 — Auto-discovery (like Django's `manage.py`)

Create a `commands/` folder next to your entry point:

```
myapp/
├── cli.py
└── commands/
    ├── greet.py
    └── export.py
```

**`commands/greet.py`**

```python
from base_command import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Greet someone"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str, help="Name to greet")
        parser.add_argument("--shout", action="store_true", help="SHOUT the greeting")

    def handle(self, *args, **options):
        name = options["name"]
        if not name.strip():
            raise CommandError("Name cannot be empty.")

        msg = f"Hello, {name}!"
        if options["shout"]:
            msg = msg.upper()

        self.stdout.write(self.style.SUCCESS(msg))
```

**`cli.py`**

```python
from base_command import Runner

runner = Runner(commands_dir="commands")

if __name__ == "__main__":
    runner.run()
```

```bash
python cli.py greet Alice --shout
# HELLO, ALICE!

python cli.py greet --help
python cli.py --help
```

---

### Method 2 — Manual registry (decorator-based)

```python
from base_command import BaseCommand, CommandError, CommandRegistry

registry = CommandRegistry()

@registry.register("greet")
class GreetCommand(BaseCommand):
    help = "Greet someone"

    def add_arguments(self, parser):
        parser.add_argument("name")

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Hello, {options['name']}!"))

@registry.register("export")
class ExportCommand(BaseCommand):
    help = "Export data"

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=["csv", "json"], default="csv")

    def handle(self, *args, **options):
        self.stdout.write(f"Exporting as {options['format']}…")

if __name__ == "__main__":
    registry.run()
```

```bash
python cli.py greet Bob
python cli.py export --format json
python cli.py --help
```

---

### Method 3 — Single-command script

```python
import sys
from base_command import BaseCommand, CommandError

class Command(BaseCommand):
    help = "My tool"

    def add_arguments(self, parser):
        parser.add_argument("input_file")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if not options["dry_run"]:
            # do real work
            pass
        self.stdout.write(self.style.SUCCESS("Done."))

if __name__ == "__main__":
    Command().run_from_argv(sys.argv)
```

---

## API Reference

### `BaseCommand`

| Attribute | Type | Default | Description |
|---|---|---|---|
| `help` | `str` | `""` | Description shown in `--help` |
| `output_transaction` | `bool` | `False` | Wrap `handle()` return value in `BEGIN;` / `COMMIT;` |
| `suppressed_base_arguments` | `set[str]` | `set()` | Base option strings to hide from `--help` |
| `stealth_options` | `tuple[str]` | `()` | Options used by the command but not declared via `add_arguments()` |
| `missing_args_message` | `str \| None` | `None` | Custom message when required positional args are missing |

#### Methods to override

| Method | Required | Description |
|---|---|---|
| `handle(*args, **options)` | ✅ | Command logic. May return a string. |
| `add_arguments(parser)` | ❌ | Add command-specific arguments to the parser. |
| `get_version()` | ❌ | Override to expose your package version via `--version`. |

#### Built-in flags (always available)

| Flag | Description |
|---|---|
| `--version` | Print the version and exit |
| `-v / --verbosity` | Verbosity level: 0–3 (default 1) |
| `--traceback` | Re-raise `CommandError` instead of printing cleanly |
| `--no-color` | Disable colored output |
| `--force-color` | Force colored output even when not a TTY |

#### `__init__` parameters

```python
Command(stdout=None, stderr=None, no_color=False, force_color=False)
```

#### `self.stdout` / `self.stderr`

`OutputWrapper` instances — use these instead of `print()`:

```python
self.stdout.write("normal output")
self.stderr.write("error output")
```

#### `self.style`

Color helpers (no-ops when color is disabled):

```python
self.stdout.write(self.style.SUCCESS("It worked!"))    # green
self.stdout.write(self.style.WARNING("Be careful."))   # yellow
self.stdout.write(self.style.ERROR("Failed."))         # red
self.stdout.write(self.style.NOTICE("FYI."))           # blue
```

All available styles: `SUCCESS`, `WARNING`, `ERROR`, `NOTICE`,
`SQL_FIELD`, `SQL_COLTYPE`, `SQL_KEYWORD`, `SQL_TABLE`,
`HTTP_INFO`, `HTTP_SUCCESS`, `HTTP_REDIRECT`, `HTTP_NOT_MODIFIED`,
`HTTP_BAD_REQUEST`, `HTTP_NOT_FOUND`, `HTTP_SERVER_ERROR`,
`MIGRATE_HEADING`, `MIGRATE_LABEL`.

---

### `CommandError`

```python
raise CommandError("Something went wrong.")
raise CommandError("Fatal error.", returncode=2)
```

When raised inside `handle()` and the command is run from the CLI, it is caught, printed to stderr, and the process exits with `returncode` (default `1`).

When invoked via `call_command()`, it propagates normally.

---

### `LabelCommand`

For commands that accept one or more arbitrary string labels:

```python
from base_command import LabelCommand

class Command(LabelCommand):
    label = "filename"   # used in --help and missing_args_message
    help  = "Process one or more files"

    def handle_label(self, label, **options):
        self.stdout.write(f"Processing {label}…")
```

```bash
python cli.py process file1.txt file2.txt
```

---

### `Runner` (auto-discovery)

```python
from base_command import Runner

runner = Runner(commands_dir="commands")   # relative to the calling file
runner.run()
```

- Discovers all `*.py` files in `commands_dir` (ignores `_private.py` etc.).
- Each file must define a `Command` class that subclasses `BaseCommand`.

---

### `CommandRegistry` (manual)

```python
from base_command import CommandRegistry

registry = CommandRegistry()

@registry.register("name")
class MyCommand(BaseCommand): ...

registry.add("other", OtherCommand)    # programmatic registration

registry.run()                         # uses sys.argv
registry.run(["prog", "name", "--flag"])  # explicit argv
```

---

### `call_command`

Invoke a command from Python code (useful for testing):

```python
from base_command import call_command
import io

buf = io.StringIO()
call_command(GreetCommand, "Alice", verbosity=0, stdout=buf)
assert "Alice" in buf.getvalue()
```

Accepts either a class or an instance.  `CommandError` propagates normally.

---

## Testing your commands

```python
import io
from base_command import call_command, CommandError
import pytest

from myapp.commands.greet import Command as GreetCommand

def test_greet():
    buf = io.StringIO()
    call_command(GreetCommand, "Alice", stdout=buf)
    assert "Hello, Alice!" in buf.getvalue()

def test_greet_empty_name():
    with pytest.raises(CommandError, match="empty"):
        call_command(GreetCommand, "")
```

---

## Comparison with Django

| Feature | Django `BaseCommand` | `base-command` |
|---|---|---|
| `handle()` / `add_arguments()` | ✅ | ✅ |
| `self.stdout` / `self.stderr` | ✅ | ✅ |
| `self.style.*` | ✅ | ✅ |
| `--version` / `--verbosity` / `--traceback` | ✅ | ✅ |
| `--no-color` / `--force-color` | ✅ | ✅ |
| `CommandError` with `returncode` | ✅ | ✅ |
| `LabelCommand` | ✅ | ✅ |
| `call_command()` | ✅ | ✅ |
| `output_transaction` | ✅ | ✅ |
| `suppressed_base_arguments` | ✅ | ✅ |
| `OutputWrapper` | ✅ | ✅ |
| Auto-discovery from folder | ✅ (via `INSTALLED_APPS`) | ✅ (via `Runner`) |
| Manual registry | ❌ | ✅ (via `CommandRegistry`) |
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
