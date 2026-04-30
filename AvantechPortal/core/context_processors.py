from django.contrib.auth.models import Group, Permission, User
from django.db.models import Q

from .models import Notification, SupportTicket
from .ticketing_services import (
    IMPORTANT_PRIORITY_VALUES,
    OPEN_TICKET_STATUS_VALUES,
    can_manage_support_tickets,
    effective_priority_filter,
)


PAGE_ACCESS_RULES = {
    'dashboard': {'label': 'Dashboard', 'audience': 'All signed-in users'},
    'profile_page': {'label': 'Profile', 'audience': 'The signed-in account'},
    'notifications_list': {'label': 'Notifications', 'audience': 'All signed-in users'},
    'password_change': {'label': 'Change Password', 'audience': 'The signed-in account'},
    'send_email_verification': {'label': 'Verify Email', 'audience': 'The signed-in account'},
    'email_verification_sent': {'label': 'Email Verification Sent', 'audience': 'The signed-in account'},
    'email_verification_otp': {'label': 'Email Verification OTP', 'audience': 'The signed-in account'},
    'otp_setup': {'label': 'Security Setup', 'audience': 'The signed-in account'},
    'development_hub': {'label': 'Development', 'audience': 'All signed-in users'},
    'development_patch_notes': {'label': 'Patch Notes', 'audience': 'All signed-in users'},
    'support_tickets_list': {
        'label': 'Support Tickets',
        'perms': ['core.can_manage_supportticket'],
        'extra_roles': ['IT Support', 'IT-Support', 'ITSupport'],
        'note': 'Regular users can see tickets they created. Support admins can also see assigned and unassigned tickets.',
    },
    'support_ticket_create': {'label': 'Create Support Ticket', 'audience': 'All signed-in users'},
    'support_ticket_detail': {
        'label': 'Support Ticket Detail',
        'perms': ['core.can_manage_supportticket'],
        'extra_roles': ['IT Support', 'IT-Support', 'ITSupport'],
        'note': 'Ticket creators and assigned support users can access their own ticket records.',
    },
    'support_lockout_center': {'label': 'Login Security & Lockouts', 'perms': ['axes.view_accessattempt']},
    'system_hub': {
        'label': 'System',
        'perms': [
            'core.view_databasefile',
            'core.add_databasefile',
            'core.change_databasefile',
            'core.delete_databasefile',
        ],
    },
    'activity_logs': {'label': 'Activity Log', 'perms': ['core.view_activitylog']},
    'users_list': {'label': 'Users', 'perms': ['auth.view_user']},
    'users_create': {'label': 'Create User', 'perms': ['auth.add_user']},
    'users_update': {'label': 'Edit User', 'perms': ['auth.change_user']},
    'users_delete': {'label': 'Delete User', 'perms': ['auth.delete_user']},
    'roles_list': {'label': 'Roles', 'perms': ['auth.view_group']},
    'roles_create': {'label': 'Create Role', 'perms': ['auth.add_group']},
    'roles_update': {'label': 'Edit Role', 'perms': ['auth.change_group']},
    'roles_delete': {'label': 'Delete Role', 'perms': ['auth.delete_group']},
    'clients_list': {'label': 'Clients', 'perms': ['core.view_client']},
    'clients_create': {'label': 'Create Client', 'perms': ['core.add_client']},
    'clients_update': {'label': 'Edit Client', 'perms': ['core.change_client']},
    'clients_delete': {'label': 'Delete Client', 'perms': ['core.delete_client']},
    'clients_quote': {'label': 'Client Quotation', 'perms': ['core.change_clientquotation']},
    'clients_quotation_document': {'label': 'Client Quotation Document', 'perms': ['core.view_clientquotation']},
    'finance_dashboard': {'label': 'Finance Dashboard', 'perms': ['core.view_fundrequest']},
    'fund_requests_list': {'label': 'Fund Request', 'perms': ['core.view_fundrequest']},
    'fund_request_records': {'label': 'Fund Request Records', 'perms': ['core.view_fundrequest']},
    'fund_request_records_pdf': {'label': 'Fund Request Records PDF', 'perms': ['core.view_fundrequest']},
    'fund_request_review': {'label': 'Fund Request Review', 'perms': ['core.change_fundrequest']},
    'fund_request_document': {'label': 'Fund Request Document', 'perms': ['core.view_fundrequest']},
    'fund_request_print': {'label': 'Fund Request Print', 'perms': ['core.view_fundrequest']},
    'fund_request_client_side_preview': {'label': 'Fund Request Preview', 'perms': ['core.view_fundrequest']},
    'fund_request_template_guide': {'label': 'Fund Request Templates', 'perms': ['core.view_fundrequesttemplate']},
    'fund_request_template_preview': {'label': 'Fund Request Template Preview', 'perms': ['core.view_fundrequesttemplate']},
    'liquidation_page': {'label': 'Liquidation', 'perms': ['core.view_liquidation']},
    'finance_reimburstment': {'label': 'Reimburstment', 'perms': ['core.view_fundrequest']},
    'finance_summary_request': {'label': 'Summary Request', 'perms': ['core.view_fundrequest']},
    'assets_list': {'label': 'Assets', 'perms': ['core.view_assetitem']},
    'assets_departments_list': {'label': 'Asset Departments', 'perms': ['core.view_assetdepartment']},
    'assets_department_create': {'label': 'Create Asset Department', 'perms': ['core.add_assetdepartment']},
    'assets_department_update': {'label': 'Edit Asset Department', 'perms': ['core.change_assetdepartment']},
    'assets_department_delete': {'label': 'Delete Asset Department', 'perms': ['core.delete_assetdepartment']},
    'assets_item_create': {'label': 'Create Asset Item', 'perms': ['core.add_assetitem']},
    'assets_item_update': {'label': 'Edit Asset Item', 'perms': ['core.change_assetitem']},
    'assets_item_delete': {'label': 'Delete Asset Item', 'perms': ['core.delete_assetitem']},
    'assets_item_types_list': {'label': 'Asset Item Types', 'perms': ['core.view_assetitemtype']},
    'assets_item_type_create': {'label': 'Create Asset Item Type', 'perms': ['core.add_assetitemtype']},
    'assets_item_type_update': {'label': 'Edit Asset Item Type', 'perms': ['core.change_assetitemtype']},
    'assets_item_type_delete': {'label': 'Delete Asset Item Type', 'perms': ['core.delete_assetitemtype']},
    'assets_tag_document': {'label': 'Asset Tags & Documents', 'perms': ['core.view_assettagbatch']},
    'assets_company_accounts': {
        'label': 'Internet Accounts',
        'perms': [
            'core.view_companyinternetaccount',
            'core.add_companyinternetaccount',
            'core.change_companyinternetaccount',
        ],
    },
    'accountability_list': {'label': 'Accountability', 'perms': ['core.view_assetaccountability']},
    'accountability_create': {'label': 'Borrow Assets', 'perms': ['core.can_borrow_assets']},
    'accountability_form_batch_create': {'label': 'Accountability Forms', 'perms': ['core.change_assetaccountability']},
    'accountability_report_summary': {'label': 'Accountability Summary Report', 'perms': ['core.view_assetaccountability']},
    'accountability_report_list': {'label': 'Accountability List Report', 'perms': ['core.view_assetaccountability']},
}


def _split_permission_name(permission_name):
    if '.' not in permission_name:
        return '', permission_name
    app_label, codename = permission_name.split('.', 1)
    return app_label, codename


def _permissions_for_names(permission_names):
    lookups = [_split_permission_name(permission_name) for permission_name in permission_names]
    query = Q()
    for app_label, codename in lookups:
        if app_label and codename:
            query |= Q(content_type__app_label=app_label, codename=codename)
    if not query:
        return Permission.objects.none()
    return Permission.objects.filter(query).select_related('content_type')


def _display_user(user):
    return user.get_full_name() or user.username


def _build_permission_access(rule):
    permission_names = rule.get('perms') or []
    permissions = list(_permissions_for_names(permission_names))
    permission_ids = [permission.id for permission in permissions]
    permission_labels = [
        str(permission.name or permission.codename).replace('Can ', '').replace('can ', '').capitalize()
        for permission in permissions
    ]

    role_query = Q(pk__in=[])
    if permission_ids:
        role_query = Q(permissions__id__in=permission_ids)
    extra_roles = rule.get('extra_roles') or []
    if extra_roles:
        role_query |= Q(name__in=extra_roles)
    roles = list(Group.objects.filter(role_query).distinct().order_by('name').values_list('name', flat=True))

    user_query = Q(is_superuser=True)
    if permission_ids:
        user_query |= Q(user_permissions__id__in=permission_ids)
        user_query |= Q(user_permissions__isnull=True, groups__permissions__id__in=permission_ids)
    if extra_roles:
        user_query |= Q(user_permissions__isnull=True, groups__name__in=extra_roles)

    users = [
        _display_user(user)
        for user in User.objects.filter(is_active=True).filter(user_query).distinct().order_by('first_name', 'last_name', 'username')[:30]
    ]
    total_users = User.objects.filter(is_active=True).filter(user_query).distinct().count()

    return {
        'roles': roles,
        'users': users,
        'total_users': total_users,
        'permissions': permission_labels,
    }


def page_access_indicator(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_superuser:
        return {'page_access_indicator': None}

    resolver_match = getattr(request, 'resolver_match', None)
    url_name = getattr(resolver_match, 'url_name', '') or ''
    rule = PAGE_ACCESS_RULES.get(url_name)
    if not rule:
        return {'page_access_indicator': None}

    indicator = {
        'label': rule.get('label') or url_name.replace('_', ' ').title(),
        'audience': rule.get('audience', ''),
        'note': rule.get('note', ''),
        'roles': [],
        'users': [],
        'total_users': 0,
        'permissions': [],
    }

    if rule.get('perms') or rule.get('extra_roles'):
        indicator.update(_build_permission_access(rule))

    return {'page_access_indicator': indicator}


def notification_summary(request):
    if not request.user.is_authenticated:
        return {
            'notifications': [],
            'unread_notification_count': 0,
        }

    notifications = list(
        Notification.objects.filter(user=request.user, is_read=False)
        .order_by('-created_at')[:5]
    )
    unread_notification_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'notifications': notifications,
        'unread_notification_count': unread_notification_count,
    }


def finance_navigation_state(request):
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = getattr(resolver_match, 'url_name', '') or ''
    is_finance_nav_active = (
        url_name.startswith('finance_')
        or url_name.startswith('fund_request')
        or url_name.startswith('liquidation')
    )
    is_asset_tracker_nav_active = (
        url_name.startswith('assets_')
        or url_name.startswith('accountability')
    )
    is_support_ticket_nav_active = url_name.startswith('support_ticket')

    important_ticket_count = 0
    if request.user.is_authenticated:
        important_query = SupportTicket.objects.filter(
            status__in=OPEN_TICKET_STATUS_VALUES,
            is_archived=False,
        ).filter(
            effective_priority_filter(IMPORTANT_PRIORITY_VALUES[0]) | effective_priority_filter(IMPORTANT_PRIORITY_VALUES[1])
        )
        if request.user.is_superuser:
            important_ticket_count = important_query.count()
        elif can_manage_support_tickets(request.user):
            important_ticket_count = important_query.filter(
                Q(assigned_to=request.user) | Q(assigned_to__isnull=True) | Q(created_by=request.user)
            ).count()
        else:
            important_ticket_count = important_query.filter(created_by=request.user).count()

    return {
        'is_finance_nav_active': is_finance_nav_active,
        'is_asset_tracker_nav_active': is_asset_tracker_nav_active,
        'is_support_ticket_nav_active': is_support_ticket_nav_active,
        'important_ticket_count': important_ticket_count,
    }
