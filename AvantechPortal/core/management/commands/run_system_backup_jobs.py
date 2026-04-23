from django.core.management.base import BaseCommand

from core.system_backup_services import run_due_system_backups


class Command(BaseCommand):
    help = 'Run due System backup schedules and create backup archives.'

    def handle(self, *args, **options):
        created = run_due_system_backups()
        if not created:
            self.stdout.write(self.style.WARNING('No due backup schedules to run.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Created {len(created)} backup(s).'))
        for backup in created:
            self.stdout.write(f'- {backup.backup_name}')
