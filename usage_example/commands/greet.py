import sys
from typing import Any

from python_base_command import BaseCommand, CommandError
from python_base_command.base import CommandParser


class Command(BaseCommand):
    help = "Greet a user by name"
    version = "1.0.0"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--name", type=str, help="Name to greet")
        parser.add_argument("--shout", action="store_true", help="Print in uppercase")

    def handle(self, *_args: Any, **kwargs: Any) -> None:
        if not (name := kwargs["name"].strip()):
            raise CommandError("Name cannot be empty.")

        msg = f"Hello, {name}!"
        if kwargs["shout"]:
            msg = msg.upper()

        self.logger.info(msg)


if __name__ == "__main__":
    Command().run_from_argv(sys.argv)
