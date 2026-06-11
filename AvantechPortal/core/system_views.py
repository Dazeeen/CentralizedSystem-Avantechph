from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db.utils import OperationalError
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .activity import record_activity
from .forms import prepare_image_upload
from .models import SuperUserChatMessage, SuperUserChatReadState, SystemBackup, SystemBackupSchedule
from .system_backup_services import (
    create_system_backup,
    get_or_create_primary_schedule,
    record_backup_created_activity,
    restore_system_backup,
    run_due_system_backups,
)
from .system_database_transfer import (
    SUPPORTED_DATABASE_VENDORS,
    build_target_database_environment,
    create_database_export_archive,
    current_database_profile,
    current_system_version,
    import_database_export_payload,
    read_database_import_payload,
    update_active_database_env,
    write_database_profile,
)

_SYSTEM_DB_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_SYSTEM_DB_JOB_TIMEOUT_SECONDS = 60 * 60 * 2


def _system_db_job_cache_key(job_id):
    return f'system_database_job:{job_id}'


def _system_db_job_get(job_id):
    return cache.get(_system_db_job_cache_key(job_id))


def _system_db_job_set(job_id, payload):
    cache.set(_system_db_job_cache_key(job_id), payload, timeout=_SYSTEM_DB_JOB_TIMEOUT_SECONDS)


def _system_db_job_update(job_id, **updates):
    payload = _system_db_job_get(job_id) or {'job_id': job_id}
    payload.update(updates)
    _system_db_job_set(job_id, payload)
    return payload


def _can_manage_system_backups(user):
    return (
        user.is_superuser
        or user.has_perm('core.view_databasefile')
        or user.has_perm('core.add_databasefile')
        or user.has_perm('core.change_databasefile')
        or user.has_perm('core.delete_databasefile')
    )


def _can_access_super_user_chat(user):
    preview = getattr(user, '_role_preview', None)
    preview_role_name = ((preview or {}).get('role_name') or '').strip().casefold()
    if preview is not None:
        return bool(user and user.is_authenticated and preview_role_name == 'super users')
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or user.groups.filter(name='Super Users').exists()
        )
    )


def _super_user_chat_unread_count(user):
    if not _can_access_super_user_chat(user):
        return 0
    unread_query = SuperUserChatMessage.objects.filter(is_deleted=False).exclude(author=user)
    read_state = SuperUserChatReadState.objects.filter(user=user).first()
    if read_state and read_state.last_seen_message_id:
        unread_query = unread_query.filter(id__gt=read_state.last_seen_message_id)
    return unread_query.count()


def _super_user_chat_signature():
    latest_changed_at = (
        SuperUserChatMessage.objects
        .order_by('-updated_at')
        .values_list('updated_at', flat=True)
        .first()
    )
    total_messages = SuperUserChatMessage.objects.count()
    latest_changed_value = latest_changed_at.isoformat() if latest_changed_at else ''
    return f'{total_messages}:{latest_changed_value}', total_messages


def _is_role_preview_active(user):
    return bool(getattr(user, '_role_preview', None))


def _get_super_user_chat_page(page_number):
    chat_messages = (
        SuperUserChatMessage.objects
        .select_related('author', 'author__profile', 'deleted_by')
        .order_by('-created_at')
    )
    chat_page = Paginator(chat_messages, 50).get_page(page_number)
    return chat_messages, chat_page, list(reversed(chat_page.object_list))


def _mark_super_user_chat_seen(user):
    if _is_role_preview_active(user):
        return
    latest_message = SuperUserChatMessage.objects.filter(is_deleted=False).order_by('-id').first()
    if latest_message:
        try:
            SuperUserChatReadState.objects.update_or_create(
                user=user,
                defaults={
                    'last_seen_message': latest_message,
                    'last_seen_at': timezone.now(),
                },
            )
        except OperationalError as exc:
            if 'database is locked' not in str(exc).lower():
                raise


def _permission_denied_response(request, message='You do not have permission to perform this action.'):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'message': message}, status=403)

    messages.error(request, message, extra_tags='permission-modal')
    referer = (request.META.get('HTTP_REFERER') or '').strip()
    if referer and url_has_allowed_host_and_scheme(referer, {request.get_host()}):
        return redirect(referer)
    return redirect('dashboard')


def _parse_boolean_field(post_data, key):
    return post_data.get(key) in {'1', 'true', 'on', 'yes'}


def _format_file_size(size_bytes):
    units = ['B', 'KB', 'MB', 'GB']
    value = float(max(0, int(size_bytes or 0)))
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    if index == 0:
        return f'{int(value)} {units[index]}'
    return f'{value:.2f} {units[index]}'


@login_required
def super_user_chat(request):
    if not _can_access_super_user_chat(request.user):
        return _permission_denied_response(request, 'Only Super Users can access this chat.')

    if request.method == 'POST':
        message_text = (request.POST.get('message') or '').strip()
        if len(message_text) > 2000:
            messages.error(request, 'Message must be 2000 characters or less.')
            return redirect('super_user_chat')
        image_upload = request.FILES.get('image')
        if not message_text and not image_upload:
            messages.warning(request, 'Message cannot be empty.')
            return redirect('super_user_chat')
        if image_upload:
            try:
                image_upload = prepare_image_upload(
                    image_upload,
                    max_size_bytes=10 * 1024 * 1024,
                    label='chat photo',
                )
            except ValidationError as exc:
                messages.error(request, '; '.join(exc.messages))
                return redirect('super_user_chat')

        chat_message = SuperUserChatMessage.objects.create(
            author=request.user,
            message=message_text,
            image=image_upload,
        )
        record_activity(
            request,
            'create',
            'system',
            'Posted a Super User Chat message.',
            target=chat_message,
            target_label=f'Message #{chat_message.id}',
            metadata={'message_id': chat_message.id, 'has_image': bool(image_upload)},
        )
        return redirect('super_user_chat')

    chat_messages, chat_page, chat_page_messages = _get_super_user_chat_page(request.GET.get('page'))
    chat_signature, total_messages = _super_user_chat_signature()
    _mark_super_user_chat_seen(request.user)

    return render(
        request,
        'core/super_user_chat.html',
        {
            'chat_page': chat_page,
            'chat_page_messages': chat_page_messages,
            'chat_signature': chat_signature,
            'total_messages': total_messages,
        },
    )


@login_required
def super_user_chat_messages(request):
    if not _can_access_super_user_chat(request.user):
        return JsonResponse({'ok': False, 'message': 'Only Super Users can access this chat.'}, status=403)

    _, chat_page, chat_page_messages = _get_super_user_chat_page(request.GET.get('page'))
    chat_signature, total_messages = _super_user_chat_signature()
    _mark_super_user_chat_seen(request.user)
    html = render_to_string(
        'core/includes/super_user_chat_messages.html',
        {'chat_page_messages': chat_page_messages},
        request=request,
    )
    return JsonResponse({
        'ok': True,
        'html': html,
        'signature': chat_signature,
        'total_messages': total_messages,
        'page': chat_page.number,
    })


@login_required
@require_POST
def super_user_chat_delete(request, message_id):
    if not _can_access_super_user_chat(request.user):
        return _permission_denied_response(request, 'Only Super Users can manage this chat.')

    chat_message = get_object_or_404(SuperUserChatMessage, pk=message_id)
    if chat_message.author_id != request.user.id:
        messages.error(request, 'You can only delete your own messages.')
        return redirect('super_user_chat')

    if not chat_message.is_deleted:
        message_preview = (chat_message.message or '').strip()[:180]
        had_image = bool(chat_message.image)
        chat_message.is_deleted = True
        chat_message.deleted_by = request.user
        chat_message.deleted_at = timezone.now()
        chat_message.save(update_fields=['is_deleted', 'deleted_by', 'deleted_at', 'updated_at'])
        record_activity(
            request,
            'delete',
            'system',
            'Deleted a Super User Chat message.',
            target=chat_message,
            target_label=f'Message #{chat_message.id}',
            metadata={
                'message_id': chat_message.id,
                'message_preview': message_preview,
                'had_image': had_image,
            },
        )
        messages.success(request, 'Message deleted.')

    return redirect('super_user_chat')


@login_required
def super_user_chat_unread_count(request):
    if not _can_access_super_user_chat(request.user):
        return JsonResponse({'ok': False, 'unread_count': 0}, status=403)
    return JsonResponse({'ok': True, 'unread_count': _super_user_chat_unread_count(request.user)})


@login_required
def system_hub(request):
    if not _can_manage_system_backups(request.user):
        if _can_access_super_user_chat(request.user):
            return redirect('super_user_chat')
        if request.user.has_perm('core.view_activitylog'):
            return redirect('activity_logs')
        return _permission_denied_response(request, 'You do not have permission to manage system backups.')

    if request.GET.get('run_due') == '1':
        try:
            run_due_system_backups()
        except Exception as exc:
            messages.warning(request, f'Automatic backup run skipped due to an error: {exc}')
    schedule = get_or_create_primary_schedule(updated_by=request.user)

    if request.method == 'POST':
        schedule.name = (request.POST.get('name') or '').strip() or 'Primary Backup Schedule'
        schedule.is_enabled = _parse_boolean_field(request.POST, 'is_enabled')
        schedule.job_type = (request.POST.get('job_type') or 'backup_cleanup').strip()

        raw_cron_minute = (request.POST.get('cron_minute') or '0').strip()
        raw_max_backups = (request.POST.get('max_backups') or '10').strip()

        try:
            schedule.cron_minute = int(raw_cron_minute)
        except (TypeError, ValueError):
            schedule.cron_minute = 0

        try:
            schedule.max_backups = int(raw_max_backups)
        except (TypeError, ValueError):
            schedule.max_backups = 10

        schedule.include_logs = _parse_boolean_field(request.POST, 'include_logs')
        schedule.include_docs = _parse_boolean_field(request.POST, 'include_docs')
        schedule.include_media = _parse_boolean_field(request.POST, 'include_media')
        schedule.include_database = _parse_boolean_field(request.POST, 'include_database')
        schedule.include_static = _parse_boolean_field(request.POST, 'include_static')
        schedule.include_templates = _parse_boolean_field(request.POST, 'include_templates')
        schedule.updated_by = request.user

        try:
            schedule.full_clean()
            schedule.save()
            record_activity(
                request,
                'update',
                'backup',
                'Updated system backup schedule.',
                target=schedule,
                target_label=schedule.name,
                metadata={'job_type': schedule.job_type, 'max_backups': schedule.max_backups},
            )
            messages.success(request, 'System backup schedule updated successfully.')
        except Exception as exc:
            messages.error(request, f'Unable to update schedule: {exc}')

        return redirect('system_hub')

    backups_queryset = SystemBackup.objects.select_related('created_by').order_by('-created_at')
    backups_page = Paginator(backups_queryset, 12).get_page(request.GET.get('page'))

    selected_scopes = [
        scope for scope, enabled in [
            ('logs', schedule.include_logs),
            ('docs', schedule.include_docs),
            ('media', schedule.include_media),
            ('database', schedule.include_database),
            ('static', schedule.include_static),
            ('templates', schedule.include_templates),
        ] if enabled
    ]

    context = {
        'schedule': schedule,
        'backups_page': backups_page,
        'selected_scopes': selected_scopes,
        'cron_expression': f'{schedule.cron_minute} * * * *',
        'format_file_size': _format_file_size,
        'current_system_version': current_system_version(),
        'current_database_profile': current_database_profile(),
    }
    return render(request, 'core/system_hub.html', context)


def _run_system_database_export_job(job_id, user_id):
    temp_path = None
    try:
        _system_db_job_update(job_id, status='running', progress=15, message='Preparing portable export...', started_at=timezone.now().isoformat())
        temp_path, filename, manifest = create_database_export_archive()
        _system_db_job_update(job_id, status='running', progress=85, message='Finalizing export archive...')
        _system_db_job_update(
            job_id,
            status='completed',
            progress=100,
            message='Database export is ready to download.',
            finished_at=timezone.now().isoformat(),
            filename=filename,
            file_path=str(temp_path),
            manifest=manifest,
            user_id=user_id,
        )
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        _system_db_job_update(job_id, status='failed', progress=100, message=str(exc) or 'Database export failed.', finished_at=timezone.now().isoformat(), user_id=user_id)


def _run_system_database_migration_job(job_id, user_id, target_config):
    temp_path = None
    try:
        target_database, target_env, _profile_dir = build_target_database_environment(target_config)
        target_label = SUPPORTED_DATABASE_VENDORS.get(target_database, target_database)
        _system_db_job_update(job_id, status='running', progress=8, message=f'Exporting current data before switching to {target_label}...', started_at=timezone.now().isoformat())
        temp_path, filename, manifest = create_database_export_archive(target_database_vendor=target_database, archive_kind='migration')

        command_env = os.environ.copy()
        command_env.update(target_env)
        manage_py = settings.BASE_DIR / 'manage.py'
        _system_db_job_update(job_id, status='running', progress=32, message=f'Running Django migrations on {target_label}...')
        migrate_result = subprocess.run(
            [sys.executable, str(manage_py), 'migrate', '--noinput'],
            cwd=str(settings.BASE_DIR),
            env=command_env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if migrate_result.returncode != 0:
            raise RuntimeError((migrate_result.stderr or migrate_result.stdout or 'Target database migration failed.').strip())

        _system_db_job_update(job_id, status='running', progress=62, message=f'Importing current data into {target_label}...')
        import_result = subprocess.run(
            [sys.executable, str(manage_py), 'import_portable_database', str(temp_path)],
            cwd=str(settings.BASE_DIR),
            env=command_env,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        if import_result.returncode != 0:
            raise RuntimeError((import_result.stderr or import_result.stdout or 'Target database import failed.').strip())

        _system_db_job_update(job_id, status='running', progress=88, message='Activating new database configuration for next restart...')
        env_path = update_active_database_env(target_env)
        profile_path = write_database_profile(target_config, target_env)
        temp_path.unlink(missing_ok=True)
        _system_db_job_update(
            job_id,
            status='completed',
            progress=100,
            message=f'{target_label} is now configured as the system database. Restart the server to use it.',
            finished_at=timezone.now().isoformat(),
            manifest=manifest,
            env_file=str(env_path),
            profile_path=str(profile_path),
            target_database=target_database,
            user_id=user_id,
        )
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        _system_db_job_update(job_id, status='failed', progress=100, message=str(exc) or 'Database migration failed.', finished_at=timezone.now().isoformat(), user_id=user_id)


def _run_system_database_import_job(job_id, user_id, upload_path, upload_name):
    try:
        _system_db_job_update(job_id, status='running', progress=10, message='Reading import file...', started_at=timezone.now().isoformat())

        class TempUpload:
            def __init__(self, path, name):
                self.path = Path(path)
                self.name = name

            def read(self):
                return self.path.read_bytes()

        payload = read_database_import_payload(TempUpload(upload_path, upload_name))
        _system_db_job_update(job_id, status='running', progress=30, message='Validating version and schema...')
        summary = import_database_export_payload(payload)
        _system_db_job_update(job_id, status='running', progress=90, message='Finalizing import summary...')
        totals = {'added': 0, 'updated': 0, 'removed': 0}
        for model_summary in summary.get('models', {}).values():
            for key in totals:
                totals[key] += int(model_summary.get(key) or 0)
        message = f'Database import complete. Added: {totals["added"]}, updated: {totals["updated"]}, removed: {totals["removed"]}.'
        _system_db_job_update(
            job_id,
            status='completed',
            progress=100,
            message=message,
            finished_at=timezone.now().isoformat(),
            summary=summary,
            totals=totals,
            user_id=user_id,
        )
    except Exception as exc:
        _system_db_job_update(job_id, status='failed', progress=100, message=str(exc) or 'Database import failed.', finished_at=timezone.now().isoformat(), user_id=user_id)
    finally:
        Path(upload_path).unlink(missing_ok=True)


@login_required
def system_database_job_status(request, job_id):
    if not _can_manage_system_backups(request.user):
        return JsonResponse({'ok': False, 'message': 'You do not have permission to view database jobs.'}, status=403)
    job = _system_db_job_get(job_id)
    if not job:
        return JsonResponse({'ok': False, 'status': 'not_found', 'message': 'Database job not found.'}, status=404)
    if int(job.get('user_id') or 0) != request.user.id and not request.user.is_superuser:
        return JsonResponse({'ok': False, 'message': 'You do not have permission to view this database job.'}, status=403)
    return JsonResponse({'ok': True, **job})


@login_required
def system_database_job_download(request, job_id):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to download database job files.')
    job = _system_db_job_get(job_id)
    if not job or job.get('status') != 'completed' or not job.get('file_path'):
        messages.error(request, 'Database job file is not ready.')
        return redirect('system_hub')
    if int(job.get('user_id') or 0) != request.user.id and not request.user.is_superuser:
        return _permission_denied_response(request, 'You do not have permission to download this database job file.')
    file_path = Path(job.get('file_path'))
    if not file_path.exists():
        messages.error(request, 'Database job file is missing or expired.')
        return redirect('system_hub')
    return FileResponse(file_path.open('rb'), as_attachment=True, filename=job.get('filename') or 'database_job.zip')


@login_required
@require_POST
def system_database_export_start(request):
    if not _can_manage_system_backups(request.user):
        return JsonResponse({'ok': False, 'message': 'You do not have permission to export database data.'}, status=403)
    job_id = uuid.uuid4().hex
    _system_db_job_set(job_id, {'job_id': job_id, 'type': 'export', 'status': 'queued', 'progress': 3, 'message': 'Export queued.', 'user_id': request.user.id})
    _SYSTEM_DB_JOB_EXECUTOR.submit(_run_system_database_export_job, job_id, request.user.id)
    return JsonResponse({'ok': True, 'job_id': job_id, 'message': 'Database export started.'})


@login_required
@require_POST
def system_database_migration_start(request):
    if not _can_manage_system_backups(request.user):
        return JsonResponse({'ok': False, 'message': 'You do not have permission to migrate database data.'}, status=403)
    target_database = (request.POST.get('target_database') or '').strip().lower()
    if target_database not in SUPPORTED_DATABASE_VENDORS:
        return JsonResponse({'ok': False, 'message': 'Please select a supported target database.'}, status=400)
    target_config = {
        'vendor': target_database,
        'name': (request.POST.get('database_name') or '').strip(),
        'file': (request.POST.get('database_file') or '').strip(),
        'host': (request.POST.get('database_host') or '').strip(),
        'port': (request.POST.get('database_port') or '').strip(),
        'user': (request.POST.get('database_user') or '').strip(),
        'password': (request.POST.get('database_password') or '').strip(),
    }
    job_id = uuid.uuid4().hex
    _system_db_job_set(job_id, {'job_id': job_id, 'type': 'migration', 'status': 'queued', 'progress': 3, 'message': 'Migration package queued.', 'target_database': target_database, 'user_id': request.user.id})
    _SYSTEM_DB_JOB_EXECUTOR.submit(_run_system_database_migration_job, job_id, request.user.id, target_config)
    return JsonResponse({'ok': True, 'job_id': job_id, 'message': 'Database migration started.'})


@login_required
def system_database_export(request):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to export database data.')

    temp_path = None
    try:
        temp_path, filename, manifest = create_database_export_archive()
        record_activity(
            request,
            'generate',
            'system',
            f'Exported database data for system v{current_system_version()}.',
            target_label=filename,
            metadata={
                'system_version': current_system_version(),
                'data_hash': manifest.get('data_hash'),
                'source_database': manifest.get('source_database', {}),
                'schema_signature': manifest.get('schema_signature'),
                'model_counts': manifest.get('model_counts', {}),
            },
        )
        archive_bytes = temp_path.read_bytes()
        temp_path.unlink(missing_ok=True)
        response = HttpResponse(archive_bytes, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        messages.error(request, f'Database export failed: {exc}')
        return redirect('system_hub')


@login_required
@require_POST
def system_database_import(request):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to import database data.')

    upload = request.FILES.get('database_import_file')
    if not upload:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': 'Please choose a database export file to import.'}, status=400)
        messages.error(request, 'Please choose a database export file to import.')
        return redirect('system_hub')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        with tempfile.NamedTemporaryFile(suffix=Path(upload.name or 'database-import.zip').suffix or '.zip', delete=False) as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            upload_path = tmp.name
        job_id = uuid.uuid4().hex
        _system_db_job_set(job_id, {'job_id': job_id, 'type': 'import', 'status': 'queued', 'progress': 3, 'message': 'Import queued.', 'user_id': request.user.id})
        _SYSTEM_DB_JOB_EXECUTOR.submit(_run_system_database_import_job, job_id, request.user.id, upload_path, upload.name or 'database-import.zip')
        return JsonResponse({'ok': True, 'job_id': job_id, 'message': 'Database import started.'})

    try:
        payload = read_database_import_payload(upload)
        summary = import_database_export_payload(payload)
    except Exception as exc:
        messages.error(request, f'Database import rejected: {exc}')
        return redirect('system_hub')

    totals = {'added': 0, 'updated': 0, 'removed': 0}
    for model_summary in summary.get('models', {}).values():
        for key in totals:
            totals[key] += int(model_summary.get(key) or 0)
    try:
        record_activity(
            request,
            'restore',
            'system',
            f'Imported database data for system v{current_system_version()}.',
            metadata={
                'system_version': current_system_version(),
                'data_hash': summary.get('data_hash'),
                'source_database': summary.get('source_database', {}),
                'target_database': summary.get('target_database', {}),
                'schema_signature': summary.get('schema_signature'),
                'sequence_resets': summary.get('sequence_resets', 0),
                'totals': totals,
            },
        )
    except Exception:
        pass
    messages.success(
        request,
        f'Database import complete. Added: {totals["added"]}, updated: {totals["updated"]}, removed: {totals["removed"]}.',
    )
    return redirect('system_hub')


@login_required
@require_POST
def system_backup_run_now(request):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to create backups.')

    schedule = get_or_create_primary_schedule(updated_by=request.user)
    try:
        backup = create_system_backup(schedule, created_by=request.user, trigger='manual')
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        messages.error(request, f'Backup creation failed: {exc}')
    else:
        record_backup_created_activity(backup, request=request)
        messages.success(request, f'Backup created: {backup.backup_name}')

    return redirect('system_hub')


@login_required
def system_backup_download(request, backup_id):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to download backups.')

    backup = get_object_or_404(SystemBackup, pk=backup_id)
    if not backup.archive:
        messages.error(request, 'Backup archive file is missing.')
        return redirect('system_hub')

    return FileResponse(
        backup.archive.open('rb'),
        as_attachment=True,
        filename=f'{backup.backup_name}.zip',
    )


@login_required
def system_backup_open(request, backup_id):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to open backups.')

    backup = get_object_or_404(SystemBackup, pk=backup_id)
    if not backup.archive:
        messages.error(request, 'Backup archive file is missing.')
        return redirect('system_hub')

    return redirect(backup.archive.url)


@login_required
@require_POST
def system_backup_restore(request, backup_id):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to restore backups.')

    backup = get_object_or_404(SystemBackup, pk=backup_id)
    try:
        restore_system_backup(backup)
        record_activity(
            request,
            'restore',
            'backup',
            f'Restored system backup {backup.backup_name}.',
            target=backup,
            target_label=backup.backup_name,
        )
        messages.success(request, f'Backup restored: {backup.backup_name}')
    except Exception as exc:
        messages.error(request, f'Unable to restore backup: {exc}')

    return redirect('system_hub')


@login_required
@require_POST
def system_backup_delete(request, backup_id):
    if not _can_manage_system_backups(request.user):
        return _permission_denied_response(request, 'You do not have permission to delete backups.')

    backup = get_object_or_404(SystemBackup, pk=backup_id)
    backup_name = backup.backup_name
    if backup.archive:
        backup.archive.delete(save=False)
    backup.delete()
    record_activity(
        request,
        'delete',
        'backup',
        f'Deleted system backup {backup_name}.',
        target_label=backup_name,
        metadata={'backup_id': backup_id},
    )
    messages.success(request, f'Backup deleted: {backup_name}')
    return redirect('system_hub')
