import sys

from python_base_command import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Greet a user by name"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str, help="Name to greet")
        parser.add_argument("--shout", action="store_true", help="Print in uppercase")

    def handle(self, *args, **options):
        name = options["name"].strip()
        if not name:
            raise CommandError("Name cannot be empty.")

        msg = f"Hello, {name}!"
        if options["shout"]:
            msg = msg.upper()

        self.stdout.write(self.style.SUCCESS(msg))


if __name__ == "__main__":
    Command().run_from_argv(sys.argv)
