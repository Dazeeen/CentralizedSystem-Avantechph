from __future__ import annotations

import hashlib
import json
import tempfile
import time
import zipfile
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.color import no_style
from django.core import serializers
from django.db import close_old_connections, connection, router, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.db.utils import OperationalError
from django.utils import timezone
from django.utils.text import slugify


EXPORT_FORMAT_VERSION = 1
EXPORT_DATA_MEMBER = 'database_data.json'
EXPORT_MANIFEST_MEMBER = 'manifest.json'
EXCLUDED_MODELS = {
	'admin.logentry',
	'contenttypes.contenttype',
	'auth.permission',
	'sessions.session',
}
SUPPORTED_DATABASE_VENDORS = {
	'sqlite': 'SQLite',
	'mysql': 'MySQL / MariaDB',
	'postgresql': 'PostgreSQL',
}


def current_system_version():
	return str(getattr(settings, 'APP_VERSION', '1.1.10') or '1.1.10').strip()


def current_database_profile():
	settings_dict = connection.settings_dict
	name = str(settings_dict.get('NAME') or '')
	name_label = Path(name).name if connection.vendor == 'sqlite' else name
	return {
		'vendor': connection.vendor,
		'vendor_label': SUPPORTED_DATABASE_VENDORS.get(connection.vendor, connection.vendor),
		'engine': settings_dict.get('ENGINE', ''),
		'name': name_label,
		'host': settings_dict.get('HOST', '') or '',
		'port': settings_dict.get('PORT', '') or '',
	}


def active_env_file_path():
	env_file = str(getattr(settings, 'ENV_FILE', '') or '').strip()
	if env_file:
		path = Path(env_file)
		return path if path.is_absolute() else settings.BASE_DIR / path
	app_env = str(getattr(settings, 'APP_ENV', 'development') or 'development').strip().lower()
	environment_path = settings.BASE_DIR / f'.env.{app_env}'
	if environment_path.exists():
		return environment_path
	return settings.BASE_DIR / '.env'


def normalize_database_vendor(value):
	vendor = str(value or '').strip().lower()
	alias_map = {
		'sqlite3': 'sqlite',
		'mariadb': 'mysql',
		'postgres': 'postgresql',
	}
	return alias_map.get(vendor, vendor)


def build_target_database_environment(config):
	vendor = normalize_database_vendor((config or {}).get('vendor'))
	if vendor not in SUPPORTED_DATABASE_VENDORS:
		raise ValueError('Please select a supported target database.')
	db_name = str((config or {}).get('name') or '').strip() or f'avantech_{vendor}'
	profile_dir = settings.BASE_DIR / 'database' / vendor / db_name
	profile_dir.mkdir(parents=True, exist_ok=True)
	env = {
		'DJANGO_DB_ENGINE': 'sqlite3' if vendor == 'sqlite' else vendor,
		'DJANGO_DB_NAME': f'{vendor}/{db_name}' if vendor == 'sqlite' and '/' not in db_name else db_name,
	}
	if vendor == 'sqlite':
		db_file = str((config or {}).get('file') or '').strip() or 'db.sqlite3'
		env['DJANGO_DB_FILE'] = db_file
		env['DJANGO_DB_TIMEOUT'] = str((config or {}).get('timeout') or '60')
		env['DJANGO_DB_BUSY_TIMEOUT'] = str((config or {}).get('busy_timeout') or '120000')
		env['DJANGO_SQLITE_TRANSACTION_MODE'] = str((config or {}).get('transaction_mode') or 'IMMEDIATE')
		target_file = settings.BASE_DIR / 'database' / env['DJANGO_DB_NAME'] / db_file
		target_file.parent.mkdir(parents=True, exist_ok=True)
	else:
		env['DJANGO_DB_USER'] = str((config or {}).get('user') or '').strip()
		env['DJANGO_DB_PASSWORD'] = str((config or {}).get('password') or '').strip()
		env['DJANGO_DB_HOST'] = str((config or {}).get('host') or '127.0.0.1').strip()
		env['DJANGO_DB_PORT'] = str((config or {}).get('port') or ('3306' if vendor == 'mysql' else '5432')).strip()
		env['DJANGO_DB_CONN_MAX_AGE'] = str((config or {}).get('conn_max_age') or '60')
		env['DJANGO_DB_CONNECT_TIMEOUT'] = str((config or {}).get('connect_timeout') or '10')
	return vendor, env, profile_dir


def write_database_profile(config, env_values):
	vendor, _env, profile_dir = build_target_database_environment(config)
	profile = {
		'vendor': vendor,
		'vendor_label': SUPPORTED_DATABASE_VENDORS[vendor],
		'activated_at': timezone.localtime(timezone.now()).isoformat(),
		'system_version': current_system_version(),
		'env_file': str(active_env_file_path()),
		'env_values': {key: value for key, value in env_values.items() if key != 'DJANGO_DB_PASSWORD'},
	}
	profile_path = profile_dir / 'database_profile.json'
	profile_path.write_text(json.dumps(profile, indent=2), encoding='utf-8')
	return profile_path


def update_active_database_env(env_values):
	env_path = active_env_file_path()
	env_path.parent.mkdir(parents=True, exist_ok=True)
	lines = env_path.read_text(encoding='utf-8').splitlines() if env_path.exists() else []
	updates = {str(k): str(v) for k, v in env_values.items()}
	seen = set()
	next_lines = []
	for line in lines:
		stripped = line.strip()
		if not stripped or stripped.startswith('#') or '=' not in line:
			next_lines.append(line)
			continue
		key = line.split('=', 1)[0].strip()
		if key in updates:
			next_lines.append(f'{key}={updates[key]}')
			seen.add(key)
		else:
			next_lines.append(line)
	for key, value in updates.items():
		if key not in seen:
			next_lines.append(f'{key}={value}')
	env_path.write_text('\n'.join(next_lines).rstrip() + '\n', encoding='utf-8')
	return env_path


def current_migration_state():
	try:
		applied = MigrationRecorder(connection).applied_migrations()
	except Exception:
		return []
	return [
		{'app': app_label, 'name': migration_name}
		for app_label, migration_name in sorted(applied)
	]


def current_schema_signature():
	return _sha256_json(current_migration_state())


def _exportable_models():
	models = []
	for model in apps.get_models():
		label = model._meta.label_lower
		if label in EXCLUDED_MODELS:
			continue
		if model._meta.proxy or not model._meta.managed:
			continue
		if not router.allow_migrate_model('default', model):
			continue
		models.append(model)
	return models


def _model_payload(model):
	queryset = model._default_manager.all().order_by(model._meta.pk.name)
	return json.loads(serializers.serialize('json', queryset))


def _canonical_json(value):
	return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _sha256_json(value):
	return hashlib.sha256(_canonical_json(value).encode('utf-8')).hexdigest()


def build_database_export_payload(target_database_vendor=''):
	model_payloads = {}
	model_counts = {}
	model_hashes = {}
	source_database = current_database_profile()
	target_database_vendor = str(target_database_vendor or '').strip().lower()
	target_database = {}
	if target_database_vendor:
		if target_database_vendor not in SUPPORTED_DATABASE_VENDORS:
			raise ValueError(f'Unsupported target database: {target_database_vendor}.')
		target_database = {
			'vendor': target_database_vendor,
			'vendor_label': SUPPORTED_DATABASE_VENDORS[target_database_vendor],
		}
	migration_state = current_migration_state()
	schema_signature = _sha256_json(migration_state)
	for model in _exportable_models():
		label = model._meta.label_lower
		payload = _model_payload(model)
		model_payloads[label] = payload
		model_counts[label] = len(payload)
		model_hashes[label] = _sha256_json(payload)

	data = {
		'format': 'avantech-database-data',
		'format_version': EXPORT_FORMAT_VERSION,
		'system_version': current_system_version(),
		'exported_at': timezone.localtime(timezone.now()).isoformat(),
		'source_database': source_database,
		'target_database': target_database,
		'supported_target_databases': SUPPORTED_DATABASE_VENDORS,
		'migration_state': migration_state,
		'schema_signature': schema_signature,
		'models': model_payloads,
	}
	manifest = {
		'format': data['format'],
		'format_version': EXPORT_FORMAT_VERSION,
		'system_version': data['system_version'],
		'exported_at': data['exported_at'],
		'source_database': source_database,
		'target_database': target_database,
		'supported_target_databases': SUPPORTED_DATABASE_VENDORS,
		'schema_signature': schema_signature,
		'model_counts': model_counts,
		'model_hashes': model_hashes,
		'data_hash': _sha256_json(model_payloads),
	}
	return data, manifest


def create_database_export_archive(target_database_vendor='', archive_kind='export'):
	data, manifest = build_database_export_payload(target_database_vendor=target_database_vendor)
	timestamp = timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')
	version_slug = slugify(current_system_version()) or 'version'
	kind_slug = slugify(archive_kind or 'export') or 'export'
	target_slug = slugify(target_database_vendor or '') or ''
	if target_slug:
		archive_name = f'avantech_database_{kind_slug}_to_{target_slug}_v{version_slug}_{timestamp}.zip'
	else:
		archive_name = f'avantech_database_{kind_slug}_v{version_slug}_{timestamp}.zip'
	with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
		temp_path = Path(tmp.name)
	with zipfile.ZipFile(temp_path, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
		archive.writestr(EXPORT_MANIFEST_MEMBER, json.dumps(manifest, indent=2, ensure_ascii=False))
		archive.writestr(EXPORT_DATA_MEMBER, json.dumps(data, indent=2, ensure_ascii=False))
	return temp_path, archive_name, manifest


def read_database_import_payload(uploaded_file):
	raw = uploaded_file.read()
	name = (getattr(uploaded_file, 'name', '') or '').lower()
	if name.endswith('.zip'):
		with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
			temp_path = Path(tmp.name)
			tmp.write(raw)
		try:
			with zipfile.ZipFile(temp_path, mode='r') as archive:
				with archive.open(EXPORT_DATA_MEMBER) as data_file:
					return json.loads(data_file.read().decode('utf-8'))
		finally:
			temp_path.unlink(missing_ok=True)
	return json.loads(raw.decode('utf-8'))


def validate_database_import_payload(payload):
	if not isinstance(payload, dict):
		raise ValueError('Invalid database import file.')
	if payload.get('format') != 'avantech-database-data':
		raise ValueError('This file is not an Avantech database data export.')
	if int(payload.get('format_version') or 0) != EXPORT_FORMAT_VERSION:
		raise ValueError('Unsupported database export format version.')
	incoming_version = str(payload.get('system_version') or '').strip()
	if incoming_version != current_system_version():
		raise ValueError(
			f'System version mismatch. Export version is v{incoming_version or "unknown"}, '
			f'current system version is v{current_system_version()}.'
		)
	if not isinstance(payload.get('models'), dict):
		raise ValueError('Database export has no model data.')
	export_schema_signature = str(payload.get('schema_signature') or '').strip()
	current_signature = current_schema_signature()
	if export_schema_signature and export_schema_signature != current_signature:
		raise ValueError('Database schema mismatch. Run migrations or use an export from the same schema before importing.')
	if connection.vendor not in SUPPORTED_DATABASE_VENDORS:
		raise ValueError(f'Current database backend "{connection.vendor}" is not supported by the portable importer.')


def _objects_for_model(payload, model_label):
	objects = payload.get('models', {}).get(model_label, [])
	if not isinstance(objects, list):
		raise ValueError(f'Invalid data for {model_label}.')
	return objects


def _primary_keys_from_objects(objects):
	pks = set()
	for obj in objects:
		pk = obj.get('pk') if isinstance(obj, dict) else None
		if pk is not None:
			pks.add(pk)
	return pks


def _is_database_locked_error(exc):
	return 'database is locked' in str(exc).lower()


def _prepare_sqlite_for_bulk_import():
	if connection.vendor != 'sqlite':
		return
	with connection.cursor() as cursor:
		cursor.execute('PRAGMA busy_timeout=120000')


def _reset_database_sequences(models):
	sql_statements = connection.ops.sequence_reset_sql(no_style(), models)
	if not sql_statements:
		return 0
	with connection.cursor() as cursor:
		for statement in sql_statements:
			cursor.execute(statement)
	return len(sql_statements)


def _import_database_export_payload_once(payload):
	validate_database_import_payload(payload)
	models_by_label = {model._meta.label_lower: model for model in _exportable_models()}
	incoming_labels = set(payload.get('models', {}).keys())
	unknown_labels = sorted(incoming_labels - set(models_by_label.keys()))
	if unknown_labels:
		raise ValueError(f'Export contains unsupported model data: {", ".join(unknown_labels[:8])}.')
	ordered_models = [model for model in _exportable_models() if model._meta.label_lower in incoming_labels]

	summary = {
		'system_version': current_system_version(),
		'imported_at': timezone.localtime(timezone.now()).isoformat(),
		'data_hash': _sha256_json(payload.get('models', {})),
		'source_database': payload.get('source_database') or {},
		'target_database': current_database_profile(),
		'schema_signature': current_schema_signature(),
		'sequence_resets': 0,
		'models': {},
	}

	with transaction.atomic():
		with connection.constraint_checks_disabled():
			for model in ordered_models:
				model_label = model._meta.label_lower
				objects = _objects_for_model(payload, model_label)
				incoming_pks = _primary_keys_from_objects(objects)
				existing_pks = set(model._default_manager.values_list(model._meta.pk.name, flat=True))
				summary['models'][model_label] = {
					'added': len(incoming_pks - existing_pks),
					'updated': len(incoming_pks & existing_pks),
					'removed': 0,
					'imported': len(incoming_pks),
				}

			for model in ordered_models:
				model_label = model._meta.label_lower
				objects = _objects_for_model(payload, model_label)
				serialized = json.dumps(objects, ensure_ascii=False)
				for deserialized in serializers.deserialize('json', serialized, ignorenonexistent=True):
					deserialized.save()

			for model in reversed(ordered_models):
				model_label = model._meta.label_lower
				incoming_pks = _primary_keys_from_objects(_objects_for_model(payload, model_label))
				delete_queryset = model._default_manager.exclude(pk__in=incoming_pks)
				removed_count = delete_queryset.count()
				if removed_count:
					delete_queryset.delete()
				summary['models'][model_label]['removed'] = removed_count

		connection.check_constraints()
		summary['sequence_resets'] = _reset_database_sequences(ordered_models)

	return summary


def import_database_export_payload(payload, max_attempts=8):
	validate_database_import_payload(payload)
	last_error = None
	for attempt in range(1, max_attempts + 1):
		try:
			close_old_connections()
			_prepare_sqlite_for_bulk_import()
			return _import_database_export_payload_once(payload)
		except OperationalError as exc:
			if not _is_database_locked_error(exc) or attempt >= max_attempts:
				raise
			last_error = exc
			close_old_connections()
			time.sleep(min(0.75 * attempt, 5.0))
	if last_error:
		raise last_error
	raise RuntimeError('Database import failed.')
