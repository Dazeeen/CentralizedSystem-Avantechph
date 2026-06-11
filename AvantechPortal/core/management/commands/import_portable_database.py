from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.system_database_transfer import import_database_export_payload, read_database_import_payload


class Command(BaseCommand):
	help = 'Import an Avantech portable database export into the currently configured database.'

	def add_arguments(self, parser):
		parser.add_argument('archive_path', help='Path to the Avantech portable database ZIP or JSON file.')

	def handle(self, *args, **options):
		archive_path = Path(options['archive_path'])
		if not archive_path.exists():
			raise CommandError(f'Portable database file not found: {archive_path}')

		class FileUpload:
			name = archive_path.name

			def read(self):
				return archive_path.read_bytes()

		try:
			payload = read_database_import_payload(FileUpload())
			summary = import_database_export_payload(payload)
		except Exception as exc:
			raise CommandError(str(exc)) from exc

		totals = {'added': 0, 'updated': 0, 'removed': 0}
		for model_summary in summary.get('models', {}).values():
			for key in totals:
				totals[key] += int(model_summary.get(key) or 0)
		self.stdout.write(
			self.style.SUCCESS(
				f'Portable database import complete. Added: {totals["added"]}, '
				f'updated: {totals["updated"]}, removed: {totals["removed"]}.'
			)
		)
