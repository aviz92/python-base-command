from typing import Any

from python_base_command.base import BaseCommand, CommandParser
from python_base_command.registry import CommandRegistry

registry = CommandRegistry()


@registry.register("greet2")
class Greet2Command(BaseCommand):
    help = "Greet a user"

    def __init__(self) -> None:
        super().__init__()
        # self.set_project_version("python-base-command")
        self.set_project_version()

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("name", type=str)

    def handle(self, **kwargs: Any) -> None:
        self.logger.info(f"Hello, {kwargs['name']}!")


@registry.register("export")
class ExportCommand(BaseCommand):
    help = "Export data"
    version = "1.0.0"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--format", choices=["csv", "json"], default="csv")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, **kwargs: Any) -> None:
        if kwargs["dry_run"]:
            self.logger.warning("Dry run — no files written.")
            return
        self.logger.info(f"Exported as {kwargs['format']}.")


if __name__ == "__main__":
    registry.run()
