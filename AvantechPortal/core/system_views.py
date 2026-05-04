from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.http import FileResponse, JsonResponse
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
    restore_system_backup,
    run_due_system_backups,
)


def _can_manage_system_backups(user):
    return (
        user.is_superuser
        or user.has_perm('core.view_databasefile')
        or user.has_perm('core.add_databasefile')
        or user.has_perm('core.change_databasefile')
        or user.has_perm('core.delete_databasefile')
    )


def _can_access_super_user_chat(user):
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


def _get_super_user_chat_page(page_number):
    chat_messages = (
        SuperUserChatMessage.objects
        .select_related('author', 'author__profile', 'deleted_by')
        .order_by('-created_at')
    )
    chat_page = Paginator(chat_messages, 50).get_page(page_number)
    return chat_messages, chat_page, list(reversed(chat_page.object_list))


def _mark_super_user_chat_seen(user):
    latest_message = SuperUserChatMessage.objects.filter(is_deleted=False).order_by('-id').first()
    if latest_message:
        SuperUserChatReadState.objects.update_or_create(
            user=user,
            defaults={
                'last_seen_message': latest_message,
                'last_seen_at': timezone.now(),
            },
        )


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
        return _permission_denied_response(request, 'You do not have permission to manage system backups.')

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
                'system',
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
    }
    return render(request, 'core/system_hub.html', context)


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
        record_activity(
            request,
            'create',
            'system',
            f'Created system backup {backup.backup_name}.',
            target=backup,
            target_label=backup.backup_name,
            metadata={'trigger': backup.trigger, 'included_scopes': backup.included_scopes},
        )
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
            'system',
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
        'system',
        f'Deleted system backup {backup_name}.',
        target_label=backup_name,
        metadata={'backup_id': backup_id},
    )
    messages.success(request, f'Backup deleted: {backup_name}')
    return redirect('system_hub')
