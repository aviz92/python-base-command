# python-base-command

A Django-style `BaseCommand` framework for **standalone** Python CLI tools — no Django required.

---

## Installation

```bash
pip install python-base-command
```

**Dependencies:** `custom-python-logger==2.0.13` (installed automatically).

---

## Quick Start

```python
# greet.py
import sys
from base_command import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Greet a user by name"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)
        parser.add_argument("--shout", action="store_true")

    def handle(self, *args, **options):
        name = options["name"].strip()
        if not name:
            raise CommandError("Name cannot be empty.")

        msg = f"Hello, {name}!"
        if options["shout"]:
            msg = msg.upper()

        self.logger.info(msg)

if __name__ == "__main__":
    Command().run_from_argv(sys.argv)
```

```bash
python greet.py Alice
python greet.py Alice --shout
python greet.py --help
python greet.py --version
```

---

## Auto-discovery (like Django's manage.py)

```
myapp/
├── cli.py
└── commands/
    ├── greet.py
    └── export.py
```

```python
# cli.py
from base_command import Runner

if __name__ == "__main__":
    Runner(commands_dir="commands").run()
```

```bash
python cli.py greet Alice
python cli.py --help
```

---

## Manual Registry

```python
from base_command import BaseCommand, CommandError, CommandRegistry

registry = CommandRegistry()

@registry.register("greet")
class GreetCommand(BaseCommand):
    help = "Greet a user"

    def add_arguments(self, parser):
        parser.add_argument("name")

    def handle(self, *args, **options):
        self.logger.info(f"Hello, {options['name']}!")

if __name__ == "__main__":
    registry.run()
```

---

## API Reference

### `BaseCommand`

| Attribute | Type | Default | Description |
|---|---|---|---|
| `help` | `str` | `""` | Description shown in `--help` |
| `output_transaction` | `bool` | `False` | Wrap `handle()` return value in `BEGIN;` / `COMMIT;` |
| `suppressed_base_arguments` | `set[str]` | `set()` | Base flags to hide from `--help` |
| `stealth_options` | `tuple[str]` | `()` | Options used but not declared via `add_arguments()` |
| `missing_args_message` | `str \| None` | `None` | Custom message when positional args are missing |

#### Methods to override

| Method | Required | Description |
|---|---|---|
| `handle(*args, **options)` | ✅ | Command logic. May return a string. |
| `add_arguments(parser)` | ❌ | Add command-specific arguments. |
| `get_version()` | ❌ | Override to expose your package version via `--version`. |

#### `self.logger`

A `CustomLoggerAdapter` from `custom-python-logger`. Available methods:

```python
self.logger.debug("...")
self.logger.info("...")
self.logger.step("...")       # custom level for process steps
self.logger.warning("...")
self.logger.error("...")
self.logger.critical("...")
self.logger.exception("...")  # logs with traceback
```

#### Built-in flags (always available)

| Flag | Description |
|---|---|
| `--version` | Print the version and exit |
| `-v / --verbosity` | Verbosity level: 0–3 (default 1) |
| `--traceback` | Re-raise `CommandError` instead of logging cleanly |

---

### `CommandError`

```python
raise CommandError("Something went wrong.")
raise CommandError("Fatal.", returncode=2)
```

---

### `LabelCommand`

```python
from base_command import LabelCommand

class Command(LabelCommand):
    label = "filename"
    help  = "Process one or more files"

    def handle_label(self, label, **options):
        self.logger.info(f"Processing {label}...")
```

```bash
python cli.py process file1.txt file2.txt
```

---

### `Runner`

```python
from base_command import Runner

Runner(commands_dir="commands").run()
```

---

### `CommandRegistry`

```python
from base_command import CommandRegistry

registry = CommandRegistry()

@registry.register("name")
class MyCommand(BaseCommand): ...

registry.run()
```

---

### `call_command`

```python
from base_command import call_command

call_command(GreetCommand, name="Alice", verbosity=0)
```

---

## Comparison with Django

| Feature | Django `BaseCommand` | `python-base-command` |
|---|---|---|
| `handle()` / `add_arguments()` | ✅ | ✅ |
| `self.logger` (via custom-python-logger) | ❌ | ✅ |
| `self.stdout` / `self.style` | ✅ | ❌ (replaced by logger) |
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
