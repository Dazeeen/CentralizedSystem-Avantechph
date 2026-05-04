from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    prepare_image_upload,
    SupportTicketCreateForm,
    SupportTicketMessageForm,
    SupportTicketRequesterPriorityForm,
    SupportTicketSupportUpdateForm,
)
from .models import SupportTicket, SupportTicketMessage
from .activity import record_activity
from .notifications import create_notification
from .ticketing_services import (
    CLOSED_TICKET_STATUS_VALUES,
    IMPORTANT_PRIORITY_VALUES,
    OPEN_TICKET_STATUS_VALUES,
    assign_ticket_fairly,
    can_manage_support_tickets,
    effective_priority_filter,
)

def _serialize_ticket_message(message_obj):
    sender = getattr(message_obj, 'sender', None)
    sender_label = 'System'
    if sender:
        sender_label = sender.get_full_name() or sender.username
    return {
        'id': message_obj.id,
        'sender_id': message_obj.sender_id,
        'sender_label': sender_label,
        'message': message_obj.message or '',
        'image_url': message_obj.image.url if message_obj.image and not message_obj.is_deleted else '',
        'image_name': f'Ticket photo from {sender_label}',
        'is_deleted': message_obj.is_deleted,
        'created_at': timezone.localtime(message_obj.created_at).strftime('%Y-%m-%d %H:%M'),
    }


def _permission_denied_response(request, message='You do not have permission to perform this action.'):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'message': message}, status=403)

    messages.error(request, message, extra_tags='permission-modal')
    referer = (request.META.get('HTTP_REFERER') or '').strip()
    if referer and url_has_allowed_host_and_scheme(referer, {request.get_host()}):
        return redirect(referer)
    return redirect('dashboard')


def _can_access_ticket(user, ticket, can_manage=None):
    if not user or not user.is_authenticated:
        return False
    if can_manage is None:
        can_manage = can_manage_support_tickets(user)
    if user.is_superuser:
        return True
    if ticket.created_by_id == user.id or ticket.assigned_to_id == user.id:
        return True
    return bool(can_manage and ticket.assigned_to_id is None)


def _can_chat_on_ticket(user, ticket):
    if not user or not user.is_authenticated:
        return False
    if ticket.status in CLOSED_TICKET_STATUS_VALUES:
        return False
    return user.id in {ticket.created_by_id, ticket.assigned_to_id}


def _parse_selected_ticket_ids(post_data):
    parsed_ids = []
    for raw_value in post_data.getlist('ticket_ids'):
        try:
            parsed_ids.append(int(str(raw_value).strip()))
        except (TypeError, ValueError):
            continue
    return sorted(set(parsed_ids))


def _filter_ticket_search(queryset, query):
    if not query:
        return queryset
    return queryset.filter(
        Q(ticket_number__icontains=query)
        | Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(created_by__username__icontains=query)
        | Q(created_by__first_name__icontains=query)
        | Q(created_by__last_name__icontains=query)
        | Q(assigned_to__username__icontains=query)
        | Q(assigned_to__first_name__icontains=query)
        | Q(assigned_to__last_name__icontains=query)
    )


def _filter_ticket_status(queryset, status_filter, valid_statuses):
    if status_filter in valid_statuses:
        return queryset.filter(status=status_filter), status_filter
    return queryset, 'all'


def _filter_ticket_priority(queryset, priority_filter, valid_priorities):
    if priority_filter in valid_priorities:
        return queryset.filter(effective_priority_filter(priority_filter)), priority_filter
    return queryset, 'all'


@login_required
def support_tickets_list(request):
    can_manage = can_manage_support_tickets(request.user)
    is_admin = request.user.is_superuser
    query = (request.GET.get('q') or '').strip()
    status_filter = (request.GET.get('status') or 'all').strip().lower()
    priority_filter = (request.GET.get('priority') or 'all').strip().lower()
    past_query = (request.GET.get('past_q') or '').strip()
    past_status_filter = (request.GET.get('past_status') or 'all').strip().lower()
    past_priority_filter = (request.GET.get('past_priority') or 'all').strip().lower()
    archived_query = (request.GET.get('archived_q') or '').strip()
    archived_status_filter = (request.GET.get('archived_status') or 'all').strip().lower()
    archived_priority_filter = (request.GET.get('archived_priority') or 'all').strip().lower()

    visible_tickets = SupportTicket.objects.select_related('created_by', 'assigned_to').filter(is_archived=False)
    if can_manage and not request.user.is_superuser:
        visible_tickets = visible_tickets.filter(
            Q(assigned_to=request.user) | Q(created_by=request.user) | Q(assigned_to__isnull=True)
        )
    elif not can_manage:
        visible_tickets = visible_tickets.filter(created_by=request.user)

    active_tickets = visible_tickets.filter(status__in=OPEN_TICKET_STATUS_VALUES)
    past_tickets = visible_tickets.filter(status__in=CLOSED_TICKET_STATUS_VALUES)

    active_status_choices = [
        choice
        for choice in SupportTicket.STATUS_CHOICES
        if choice[0] in OPEN_TICKET_STATUS_VALUES
    ]
    past_status_choices = [
        choice
        for choice in SupportTicket.STATUS_CHOICES
        if choice[0] in CLOSED_TICKET_STATUS_VALUES
    ]
    valid_active_statuses = {choice[0] for choice in active_status_choices}
    valid_past_statuses = {choice[0] for choice in past_status_choices}
    valid_all_statuses = {choice[0] for choice in SupportTicket.STATUS_CHOICES}
    valid_priorities = {choice[0] for choice in SupportTicket.PRIORITY_CHOICES}

    ticket_queryset = _filter_ticket_search(active_tickets, query)
    ticket_queryset, status_filter = _filter_ticket_status(ticket_queryset, status_filter, valid_active_statuses)
    ticket_queryset, priority_filter = _filter_ticket_priority(ticket_queryset, priority_filter, valid_priorities)

    past_queryset = _filter_ticket_search(past_tickets, past_query)
    past_queryset, past_status_filter = _filter_ticket_status(past_queryset, past_status_filter, valid_past_statuses)
    past_queryset, past_priority_filter = _filter_ticket_priority(past_queryset, past_priority_filter, valid_priorities)

    ticket_page = Paginator(ticket_queryset.order_by('-created_at'), 10).get_page(request.GET.get('page'))
    important_open_count = active_tickets.filter(
        effective_priority_filter('high') | effective_priority_filter('critical')
    ).count()
    open_count = active_tickets.count()
    resolved_count = past_tickets.filter(status='resolved').count()
    closed_count = past_tickets.filter(status='closed').count()
    past_ticket_count = past_tickets.count()
    past_tickets_preview = past_queryset.order_by('-closed_at', '-updated_at')[:25]
    past_filtered_count = past_queryset.count()
    archived_ticket_count = 0
    archived_filtered_count = 0
    archived_tickets_preview = []
    if is_admin:
        archived_tickets_qs = SupportTicket.objects.select_related('created_by', 'assigned_to', 'archived_by').filter(is_archived=True)
        archived_ticket_count = archived_tickets_qs.count()
        archived_queryset = _filter_ticket_search(archived_tickets_qs, archived_query)
        archived_queryset, archived_status_filter = _filter_ticket_status(archived_queryset, archived_status_filter, valid_all_statuses)
        archived_queryset, archived_priority_filter = _filter_ticket_priority(archived_queryset, archived_priority_filter, valid_priorities)
        archived_filtered_count = archived_queryset.count()
        archived_tickets_preview = archived_queryset.order_by('-archived_at', '-updated_at')[:25]
    else:
        archived_status_filter = 'all'
        archived_priority_filter = 'all'

    should_open_past_modal = bool(past_query or past_status_filter != 'all' or past_priority_filter != 'all')
    should_open_archived_modal = bool(is_admin and (archived_query or archived_status_filter != 'all' or archived_priority_filter != 'all'))

    context = {
        'can_manage_support_tickets': can_manage,
        'is_admin': is_admin,
        'create_form': SupportTicketCreateForm(),
        'ticket_page': ticket_page,
        'ticket_query': query,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'open_count': open_count,
        'resolved_count': resolved_count,
        'closed_count': closed_count,
        'important_open_count': important_open_count,
        'past_ticket_count': past_ticket_count,
        'past_filtered_count': past_filtered_count,
        'past_tickets_preview': past_tickets_preview,
        'past_query': past_query,
        'past_status_filter': past_status_filter,
        'past_priority_filter': past_priority_filter,
        'should_open_past_modal': should_open_past_modal,
        'archived_ticket_count': archived_ticket_count,
        'archived_filtered_count': archived_filtered_count,
        'archived_tickets_preview': archived_tickets_preview,
        'archived_query': archived_query,
        'archived_status_filter': archived_status_filter,
        'archived_priority_filter': archived_priority_filter,
        'should_open_archived_modal': should_open_archived_modal,
        'status_choices': [('all', 'All Active Statuses')] + active_status_choices,
        'past_status_choices': [('all', 'All Past Statuses')] + past_status_choices,
        'archived_status_choices': [('all', 'All Statuses')] + list(SupportTicket.STATUS_CHOICES),
        'priority_choices': [('all', 'All Priorities')] + list(SupportTicket.PRIORITY_CHOICES),
    }
    return render(request, 'core/support_tickets_list.html', context)


@login_required
@require_POST
def support_ticket_create(request):
    form = SupportTicketCreateForm(request.POST)
    if not form.is_valid():
        for _, errors in form.errors.items():
            if errors:
                messages.error(request, errors[0])
                break
        return redirect('support_tickets_list')

    with transaction.atomic():
        ticket = form.save(commit=False)
        ticket.created_by = request.user
        ticket.status = 'open'
        ticket.last_message_at = timezone.now()
        ticket.save()
        assigned_user = assign_ticket_fairly(ticket)

    detail_url = reverse('support_ticket_detail', args=[ticket.id])
    create_notification(
        request.user,
        title='Ticket submitted',
        message=f'{ticket.ticket_number} was submitted successfully.',
        link_url=detail_url,
    )

    if assigned_user and assigned_user.id != request.user.id:
        priority_label = ticket.effective_priority.title()
        assignment_title = 'New support ticket assigned'
        if ticket.effective_priority in IMPORTANT_PRIORITY_VALUES:
            assignment_title = f'Important ticket assigned ({priority_label})'
        create_notification(
            assigned_user,
            title=assignment_title,
            message=f'{ticket.ticket_number}: {ticket.title}',
            link_url=detail_url,
        )

    record_activity(
        request,
        'create',
        'support',
        f'Created support ticket {ticket.ticket_number}.',
        target=ticket,
        target_label=ticket.ticket_number,
        metadata={'assigned_to': assigned_user.username if assigned_user else ''},
    )

    if not assigned_user:
        messages.warning(request, 'Ticket created, but no active IT Support user was found for assignment yet.')
    else:
        assignee_name = assigned_user.get_full_name() or assigned_user.username
        messages.success(request, f'Ticket created and assigned to {assignee_name}.')

    return redirect('support_ticket_detail', ticket_id=ticket.id)


@login_required
def support_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket.objects.select_related('created_by', 'assigned_to'), pk=ticket_id)
    can_manage = can_manage_support_tickets(request.user)
    if not _can_access_ticket(request.user, ticket, can_manage=can_manage):
        return _permission_denied_response(request, 'You do not have permission to view this ticket.')

    is_closed_ticket = ticket.status in CLOSED_TICKET_STATUS_VALUES
    can_chat = (not ticket.is_archived) and _can_chat_on_ticket(request.user, ticket)
    can_update_support = (not ticket.is_archived) and (can_manage or request.user.id == ticket.assigned_to_id)
    can_update_requested_priority = (
        (not ticket.is_archived)
        and (not is_closed_ticket)
        and (request.user.id == ticket.created_by_id or request.user.is_superuser)
    )
    messages_qs = ticket.messages.select_related('sender', 'deleted_by').all()

    if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
        messages_payload = [_serialize_ticket_message(message_row) for message_row in messages_qs.order_by('id')]
        latest_message_id = messages_payload[-1]['id'] if messages_payload else 0
        return JsonResponse(
            {
                'ok': True,
                'ticket_id': ticket.id,
                'messages': messages_payload,
                'latest_message_id': latest_message_id,
                'can_chat': can_chat,
            }
        )

    context = {
        'ticket': ticket,
        'messages_list': messages_qs,
        'can_manage_support_tickets': can_manage,
        'can_chat': can_chat,
        'can_update_support': can_update_support,
        'can_update_requested_priority': can_update_requested_priority,
        'is_closed_ticket': is_closed_ticket,
        'message_form': SupportTicketMessageForm(),
        'requester_priority_form': SupportTicketRequesterPriorityForm(instance=ticket),
        'support_update_form': SupportTicketSupportUpdateForm(instance=ticket),
    }
    return render(request, 'core/support_ticket_detail.html', context)


@login_required
@require_POST
def support_ticket_add_message(request, ticket_id):
    ticket = get_object_or_404(SupportTicket.objects.select_related('created_by', 'assigned_to'), pk=ticket_id)
    if ticket.is_archived:
        return _permission_denied_response(request, 'Archived tickets are read-only.')
    if ticket.status in CLOSED_TICKET_STATUS_VALUES:
        return _permission_denied_response(request, 'Closed tickets are read-only. Reopen the ticket before replying.')
    can_manage = can_manage_support_tickets(request.user)
    if not _can_access_ticket(request.user, ticket, can_manage=can_manage):
        return _permission_denied_response(request, 'You do not have permission to view this ticket.')
    if not _can_chat_on_ticket(request.user, ticket):
        return _permission_denied_response(request, 'This conversation is private to the requester and assigned IT support.')

    form = SupportTicketMessageForm(request.POST)
    if not form.is_valid():
        if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
            first_error = 'Unable to send reply.'
            for _, errors in form.errors.items():
                if errors:
                    first_error = errors[0]
                    break
            return JsonResponse({'ok': False, 'message': first_error}, status=400)
        for _, errors in form.errors.items():
            if errors:
                messages.error(request, errors[0])
                break
        return redirect('support_ticket_detail', ticket_id=ticket.id)

    image_upload = request.FILES.get('image')
    message_text = (form.cleaned_data.get('message') or '').strip()
    if not message_text and not image_upload:
        error_message = 'Message cannot be empty.'
        if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
            return JsonResponse({'ok': False, 'message': error_message}, status=400)
        messages.error(request, error_message)
        return redirect('support_ticket_detail', ticket_id=ticket.id)
    if image_upload:
        try:
            image_upload = prepare_image_upload(
                image_upload,
                max_size_bytes=10 * 1024 * 1024,
                label='ticket photo',
            )
        except ValidationError as exc:
            error_message = '; '.join(exc.messages)
            if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
                return JsonResponse({'ok': False, 'message': error_message}, status=400)
            messages.error(request, error_message)
            return redirect('support_ticket_detail', ticket_id=ticket.id)

    message = form.save(commit=False)
    message.ticket = ticket
    message.sender = request.user
    message.image = image_upload
    message.save()

    fields_to_update = ['last_message_at', 'updated_at']
    ticket.last_message_at = timezone.now()
    if request.user.id == ticket.created_by_id and ticket.status == 'waiting_user':
        ticket.status = 'open'
        ticket.closed_at = None
        fields_to_update.extend(['status', 'closed_at'])
    elif request.user.id == ticket.assigned_to_id and ticket.status == 'open':
        ticket.status = 'in_progress'
        fields_to_update.append('status')
    ticket.save(update_fields=fields_to_update)

    sender_name = request.user.get_full_name() or request.user.username
    detail_url = reverse('support_ticket_detail', args=[ticket.id])
    recipient_ids = {ticket.created_by_id, ticket.assigned_to_id}
    recipient_ids.discard(request.user.id)
    recipient_ids.discard(None)

    for user_id in recipient_ids:
        recipient = ticket.created_by if ticket.created_by_id == user_id else ticket.assigned_to
        if recipient:
            create_notification(
                recipient,
                title=f'Ticket reply: {ticket.ticket_number}',
                message=f'{sender_name}: {message.message[:90] if message.message else "Sent a photo"}',
                link_url=detail_url,
            )

    if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
        return JsonResponse({'ok': True, 'message_row': _serialize_ticket_message(message), 'latest_message_id': message.id})

    messages.success(request, 'Reply sent.')
    return redirect('support_ticket_detail', ticket_id=ticket.id)


@login_required
@require_POST
def support_ticket_message_delete(request, ticket_id, message_id):
    ticket = get_object_or_404(SupportTicket.objects.select_related('created_by', 'assigned_to'), pk=ticket_id)
    if ticket.is_archived:
        return _permission_denied_response(request, 'Archived tickets are read-only.')
    if ticket.status in CLOSED_TICKET_STATUS_VALUES:
        return _permission_denied_response(request, 'Closed tickets are read-only.')
    can_manage = can_manage_support_tickets(request.user)
    if not _can_access_ticket(request.user, ticket, can_manage=can_manage):
        return _permission_denied_response(request, 'You do not have permission to view this ticket.')

    message = get_object_or_404(SupportTicketMessage, pk=message_id, ticket=ticket)
    if message.sender_id != request.user.id:
        return _permission_denied_response(request, 'You can only delete your own messages.')

    if not message.is_deleted:
        message_preview = (message.message or '').strip()[:180]
        had_image = bool(message.image)
        message.is_deleted = True
        message.deleted_by = request.user
        message.deleted_at = timezone.now()
        message.save(update_fields=['is_deleted', 'deleted_by', 'deleted_at', 'updated_at'])
        record_activity(
            request,
            'delete',
            'support',
            f'Deleted a support ticket message in {ticket.ticket_number}.',
            target=message,
            target_label=f'{ticket.ticket_number} message #{message.id}',
            metadata={
                'ticket_id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'message_id': message.id,
                'message_preview': message_preview,
                'had_image': had_image,
            },
        )

    if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
        return JsonResponse({'ok': True, 'message_row': _serialize_ticket_message(message), 'latest_message_id': message.id})

    messages.success(request, 'Message deleted.')
    return redirect('support_ticket_detail', ticket_id=ticket.id)


@login_required
@require_POST
def support_ticket_update_requested_priority(request, ticket_id):
    ticket = get_object_or_404(SupportTicket.objects.select_related('created_by', 'assigned_to'), pk=ticket_id)
    if ticket.is_archived:
        return _permission_denied_response(request, 'Archived tickets are read-only.')
    if ticket.status in CLOSED_TICKET_STATUS_VALUES:
        return _permission_denied_response(request, 'Closed tickets are read-only.')
    if not (request.user.id == ticket.created_by_id or request.user.is_superuser):
        return _permission_denied_response(request, 'Only the ticket requester can update requested priority.')

    old_priority = ticket.requested_priority
    old_effective_priority = ticket.effective_priority
    form = SupportTicketRequesterPriorityForm(request.POST, instance=ticket)
    if not form.is_valid():
        for _, errors in form.errors.items():
            if errors:
                messages.error(request, errors[0])
                break
        return redirect('support_ticket_detail', ticket_id=ticket.id)

    updated_ticket = form.save(commit=False)
    updated_ticket.closed_at = ticket.closed_at
    updated_ticket.save(update_fields=['requested_priority', 'updated_at'])
    ticket.refresh_from_db(fields=['requested_priority', 'support_priority'])

    if old_priority != updated_ticket.requested_priority:
        detail_url = reverse('support_ticket_detail', args=[ticket.id])
        if ticket.assigned_to:
            create_notification(
                ticket.assigned_to,
                title=f'Requested priority updated ({ticket.effective_priority.title()})',
                message=f'{ticket.ticket_number}: requester changed priority.',
                link_url=detail_url,
            )
        if old_effective_priority != ticket.effective_priority and ticket.effective_priority in IMPORTANT_PRIORITY_VALUES:
            messages.warning(request, 'Priority updated to an important level (High/Critical).')
        else:
            messages.success(request, 'Requested priority updated.')
    else:
        messages.info(request, 'No priority change detected.')

    return redirect('support_ticket_detail', ticket_id=ticket.id)


@login_required
@require_POST
def support_ticket_update_support(request, ticket_id):
    ticket = get_object_or_404(SupportTicket.objects.select_related('created_by', 'assigned_to'), pk=ticket_id)
    if ticket.is_archived:
        return _permission_denied_response(request, 'Archived tickets are read-only.')
    can_manage = can_manage_support_tickets(request.user)
    if not (can_manage or request.user.id == ticket.assigned_to_id):
        return _permission_denied_response(request, 'You do not have permission to update this ticket.')

    old_status = ticket.status
    old_support_priority = ticket.support_priority or ''
    old_effective_priority = ticket.effective_priority
    form = SupportTicketSupportUpdateForm(request.POST, instance=ticket)
    if not form.is_valid():
        for _, errors in form.errors.items():
            if errors:
                messages.error(request, errors[0])
                break
        return redirect('support_ticket_detail', ticket_id=ticket.id)

    updated_ticket = form.save(commit=False)
    ticket.status = updated_ticket.status
    ticket.support_priority = updated_ticket.support_priority or None

    if ticket.status in {'resolved', 'closed'}:
        ticket.closed_at = timezone.now()
    else:
        ticket.closed_at = None

    ticket.save(update_fields=['status', 'support_priority', 'closed_at', 'updated_at'])
    if not ticket.assigned_to_id:
        assign_ticket_fairly(ticket)
        ticket.refresh_from_db(fields=['assigned_to', 'assigned_at'])

    detail_url = reverse('support_ticket_detail', args=[ticket.id])
    changed = (
        old_status != ticket.status
        or old_support_priority != (ticket.support_priority or '')
    )
    if changed:
        status_label = ticket.get_status_display()
        priority_label = ticket.effective_priority.title()
        record_activity(
            request,
            'update',
            'support',
            f'Updated support ticket {ticket.ticket_number}: {status_label}, {priority_label}.',
            target=ticket,
            target_label=ticket.ticket_number,
            metadata={'old_status': old_status, 'new_status': ticket.status, 'old_priority': old_support_priority, 'new_priority': ticket.support_priority or ''},
        )
        create_notification(
            ticket.created_by,
            title=f'Ticket updated: {ticket.ticket_number}',
            message=f'Status: {status_label} | Priority: {priority_label}',
            link_url=detail_url,
        )
        if old_effective_priority != ticket.effective_priority and ticket.effective_priority in IMPORTANT_PRIORITY_VALUES:
            messages.warning(request, 'Ticket updated with important priority (High/Critical).')
        else:
            messages.success(request, 'Ticket updated successfully.')
    else:
        messages.info(request, 'No support update changes detected.')

    return redirect('support_ticket_detail', ticket_id=ticket.id)


@login_required
@require_POST
def support_tickets_bulk_archive(request):
    if not request.user.is_superuser:
        return _permission_denied_response(request, 'Only admin can archive tickets.')

    selected_ids = _parse_selected_ticket_ids(request.POST)
    if not selected_ids:
        messages.warning(request, 'Select at least one ticket to archive.')
        return redirect('support_tickets_list')

    now = timezone.now()
    updated_count = (
        SupportTicket.objects.filter(id__in=selected_ids, is_archived=False)
        .update(
            is_archived=True,
            archived_at=now,
            archived_by=request.user,
            status='closed',
            closed_at=now,
            updated_at=now,
        )
    )
    if updated_count:
        record_activity(
            request,
            'archive',
            'support',
            f'Archived {updated_count} support ticket(s).',
            metadata={'ticket_ids': selected_ids, 'updated_count': updated_count},
        )
        messages.success(request, f'{updated_count} ticket(s) archived successfully.')
    else:
        messages.info(request, 'No eligible tickets were archived.')
    return redirect('support_tickets_list')


@login_required
@require_POST
def support_tickets_bulk_delete(request):
    if not request.user.is_superuser:
        return _permission_denied_response(request, 'Only admin can delete tickets.')

    selected_ids = _parse_selected_ticket_ids(request.POST)
    if not selected_ids:
        messages.warning(request, 'Select at least one ticket to delete.')
        return redirect('support_tickets_list')

    delete_qs = SupportTicket.objects.filter(id__in=selected_ids)
    deleted_count = delete_qs.count()
    ticket_numbers = list(delete_qs.values_list('ticket_number', flat=True))
    delete_qs.delete()
    if deleted_count:
        record_activity(
            request,
            'delete',
            'support',
            f'Deleted {deleted_count} support ticket(s).',
            metadata={'ticket_ids': selected_ids, 'ticket_numbers': ticket_numbers, 'deleted_count': deleted_count},
        )
        messages.success(request, f'{deleted_count} ticket(s) deleted successfully.')
    else:
        messages.info(request, 'No eligible tickets were deleted.')
    return redirect('support_tickets_list')
