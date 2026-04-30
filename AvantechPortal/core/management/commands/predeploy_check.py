import os

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Run safety checks before deployment."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=["deployment", "production"],
            required=True,
            help="Expected DJANGO_ENV for this deployment run.",
        )

    def handle(self, *args, **options):
        target = options["target"]
        current_env = (os.getenv("DJANGO_ENV", "development") or "development").strip().lower()

        if current_env != target:
            raise CommandError(
                f"DJANGO_ENV mismatch: expected '{target}', found '{current_env}'."
            )

        if target == "production" and settings.DEBUG:
            raise CommandError("Refusing production deployment while DEBUG=True.")

        if target == "production" and settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"):
            raise CommandError("Refusing production deployment on sqlite3. Configure PostgreSQL/MySQL first.")

        self.stdout.write("Running Django deploy checks...")
        call_command("check", "--deploy", "--fail-level", "WARNING")

        connection = connections["default"]
        executor = MigrationExecutor(connection)
        pending_plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if pending_plan:
            raise CommandError(
                f"Pending migrations detected ({len(pending_plan)}). Run migrate before deploying."
            )

        self.stdout.write(self.style.SUCCESS(f"Predeploy checks passed for '{target}' environment."))
