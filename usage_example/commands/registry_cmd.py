from typing import Any

from python_base_command import BaseCommand, CommandParser, CommandRegistry

registry = CommandRegistry()


@registry.register("greet2")
class Greet2Command(BaseCommand):
    help = "Greet a user"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("name", type=str)

    def handle(self, **kwargs: Any) -> None:
        self.logger.info(f"Hello, {kwargs['name']}!")


@registry.register("export")
class ExportCommand(BaseCommand):
    help = "Export data"

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
