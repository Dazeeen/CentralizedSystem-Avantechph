from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Q
from django.utils import timezone

from .models import (
    CalculatorSetting,
    CalculatorImportRow,
    Notification,
    SuperUserChatMessage,
    SuperUserChatReadState,
    SupportTicket,
    CRMTechnicalRecord,
    CRMTechnicalNotificationSetting,
)
from .ticketing_services import (
    IMPORTANT_PRIORITY_VALUES,
    OPEN_TICKET_STATUS_VALUES,
    can_manage_support_tickets,
    effective_priority_filter,
)

CRM_VIEW_PERMISSIONS = {
    'dashboard': ('core.view_crm_dashboard', 'core.view_client'),
    'clients': ('core.view_crm_clients_section', 'core.view_client'),
    'sales': ('core.view_crm_sales_section', 'core.view_client'),
    'technicals': ('core.view_crm_technicals_section', 'core.view_client'),
}

CRM_MANAGE_PERMISSIONS = {
    'clients': ('core.manage_crm_clients_section', 'core.change_client'),
    'sales': ('core.manage_crm_sales_section', 'core.change_client'),
    'technicals': ('core.manage_crm_technicals_section', 'core.change_client'),
}


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
        'audience': 'All signed-in users',
        'note': 'Regular users can see tickets they created. Support admins can also see assigned and unassigned tickets.',
    },
    'support_ticket_create': {'label': 'Create Support Ticket', 'audience': 'All signed-in users'},
    'support_ticket_detail': {
        'label': 'Support Ticket Detail',
        'audience': 'Ticket participants',
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
    'super_user_chat': {'label': 'Super User Chat', 'extra_roles': ['Super Users'], 'audience': 'Django superusers and members of the Super Users role'},
    'users_list': {'label': 'Users', 'perms': ['auth.view_user']},
    'users_create': {'label': 'Create User', 'perms': ['auth.add_user']},
    'users_update': {'label': 'Edit User', 'perms': ['auth.change_user']},
    'users_delete': {'label': 'Delete User', 'perms': ['auth.delete_user']},
    'roles_list': {'label': 'Roles', 'perms': ['auth.view_group']},
    'roles_create': {'label': 'Create Role', 'perms': ['auth.add_group']},
    'roles_update': {'label': 'Edit Role', 'perms': ['auth.change_group']},
    'roles_delete': {'label': 'Delete Role', 'perms': ['auth.delete_group']},
    'file_manager_list': {'label': 'File Manager', 'perms': ['core.view_managedfilenode']},
    'file_manager_search': {'label': 'File Manager Search', 'perms': ['core.view_managedfilenode']},
    'file_manager_download': {'label': 'File Manager Download', 'perms': ['core.view_managedfilenode']},
    'file_manager_preview': {'label': 'File Manager Preview', 'perms': ['core.view_managedfilenode']},
    'file_manager_setup': {'label': 'File Manager Setup', 'perms': ['core.change_managedfilenode']},
    'file_manager_browse_directories': {'label': 'File Manager Directory Browser', 'perms': ['core.change_managedfilenode']},
    'file_manager_create_folder': {'label': 'Create File Manager Folder', 'perms': ['core.add_managedfilenode']},
    'file_manager_upload': {'label': 'Upload File Manager File', 'perms': ['core.add_managedfilenode']},
    'file_manager_rename': {'label': 'Rename File Manager Item', 'perms': ['core.change_managedfilenode']},
    'file_manager_move': {'label': 'Move File Manager Item', 'perms': ['core.change_managedfilenode']},
    'file_manager_restore': {'label': 'Restore File Manager Item', 'perms': ['core.change_managedfilenode']},
    'file_manager_bulk_action': {'label': 'File Manager Bulk Action', 'perms': ['core.change_managedfilenode']},
    'clients_list': {'label': 'Clients', 'perms': ['core.view_client']},
    'clients_create': {'label': 'Create Client', 'perms': ['core.add_client']},
    'clients_update': {'label': 'Edit Client', 'perms': ['core.change_client']},
    'clients_delete': {'label': 'Delete Client', 'perms': ['core.delete_client']},
    'clients_quote': {'label': 'Client Quotation', 'perms': ['core.change_clientquotation']},
    'clients_quotation_document': {'label': 'Client Quotation Document', 'perms': ['core.view_clientquotation']},
    'crm_dashboard': {'label': 'CRM Dashboard', 'perms': ['core.view_crm_dashboard', 'core.view_client']},
    'crm_clients': {'label': 'CRM Clients', 'perms': ['core.view_crm_clients_section', 'core.view_client']},
    'crm_sales': {'label': 'CRM Sales', 'perms': ['core.view_crm_sales_section', 'core.view_client']},
    'crm_technicals': {'label': 'CRM Technicals', 'perms': ['core.view_crm_technicals_section', 'core.view_client']},
    'finance_dashboard': {'label': 'Finance Dashboard', 'perms': ['core.view_fundrequest']},
    'fund_requests_list': {'label': 'Payment Request', 'perms': ['core.view_fundrequest']},
    'fund_request_records': {'label': 'Payment Request Records', 'perms': ['core.view_fundrequest']},
    'fund_request_records_pdf': {'label': 'Payment Request Records PDF', 'perms': ['core.view_fundrequest']},
    'fund_request_review': {'label': 'Payment Request Review', 'perms': ['core.change_fundrequest']},
    'fund_request_document': {'label': 'Payment Request Document', 'perms': ['core.view_fundrequest']},
    'fund_request_print': {'label': 'Payment Request Print', 'perms': ['core.view_fundrequest']},
    'fund_request_client_side_preview': {'label': 'Payment Request Preview', 'perms': ['core.view_fundrequest']},
    'fund_request_template_guide': {'label': 'Payment Request Templates', 'perms': ['core.view_fundrequesttemplate']},
    'fund_request_template_preview': {'label': 'Payment Request Template Preview', 'perms': ['core.view_fundrequesttemplate']},
    'liquidation_page': {'label': 'Liquidation', 'perms': ['core.view_liquidation']},
    'finance_reimbursement': {'label': 'Reimbursement', 'perms': ['core.view_fundrequest']},
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
    'consumables_list': {'label': 'Consumables Inventory', 'perms': ['core.view_consumableitem']},
    'consumables_item_create': {'label': 'Create Consumable Item', 'perms': ['core.add_consumableitem']},
    'consumables_item_update': {'label': 'Edit Consumable Item', 'perms': ['core.change_consumableitem']},
    'consumables_item_delete': {'label': 'Delete Consumable Item', 'perms': ['core.delete_consumableitem']},
    'consumables_item_type_create': {'label': 'Create Consumable Type', 'perms': ['core.add_consumableitemtype']},
    'consumables_item_type_update': {'label': 'Edit Consumable Type', 'perms': ['core.change_consumableitemtype']},
    'consumables_item_type_delete': {'label': 'Delete Consumable Type', 'perms': ['core.delete_consumableitemtype']},
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

def _has_any_perm(user, permission_names):
    if user.is_superuser:
        return True
    return any(user.has_perm(permission_name) for permission_name in permission_names)


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


def role_preview(request):
    role = getattr(request, 'role_preview_role', None)
    if not role:
        return {'role_preview': None}
    return {
        'role_preview': {
            'role_id': role.id,
            'role_name': role.name,
        }
    }


def calculator_feature_flags(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {
            'enable_floating_calculator': False,
            'calculator_default_meralco_rate': '13',
            'calculator_default_sun_peak_hours': '3',
            'calculator_default_vdrop_percent': '20',
            'calculator_default_battery_health_drop_percent': '20',
        }
    try:
        calculator_settings = CalculatorSetting.load()
        enabled = bool(calculator_settings.enable_floating_calculator)
        meralco_rate = str(calculator_settings.meralco_rate)
        sun_peak_hours = str(calculator_settings.sun_peak_period_hours)
        vdrop_percent = str(calculator_settings.volt_drop_percent)
        battery_health_drop_percent = str(calculator_settings.battery_health_protection_percent)
    except (OperationalError, ProgrammingError):
        enabled = True
        meralco_rate = '13'
        sun_peak_hours = '3'
        vdrop_percent = '20'
        battery_health_drop_percent = '20'
    calculator_system_options = []
    try:
        rows = (
            CalculatorImportRow.objects
            .filter(import_record__is_active=True)
            .exclude(capacity_kw__isnull=True)
            .exclude(panel_qty__isnull=True)
            .values(
                'id',
                'system_type',
                'capacity_kw',
                'panel_qty',
                'specifications',
                'battery_ampere_hour',
                'battery_kwh',
                'warranty_panel',
                'warranty_battery',
                'warranty_inverter',
                'regular_price',
                'cash_promo_price',
            )
            .order_by('capacity_kw', 'id')
        )
        for row in rows:
            system_type = str(row.get('system_type') or '').strip()
            capacity_kw = row.get('capacity_kw')
            panel_qty = row.get('panel_qty')
            if capacity_kw is None or panel_qty is None:
                continue
            calculator_system_options.append({
                'id': int(row['id']),
                'system_type': system_type,
                'capacity_kw': float(capacity_kw),
                'panel_qty': int(panel_qty),
                'specifications': str(row.get('specifications') or '').strip(),
                'battery_ampere_hour': float(row['battery_ampere_hour']) if row.get('battery_ampere_hour') is not None else None,
                'battery_kwh': float(row['battery_kwh']) if row.get('battery_kwh') is not None else None,
                'warranty_panel': str(row.get('warranty_panel') or '').strip(),
                'warranty_battery': str(row.get('warranty_battery') or '').strip(),
                'warranty_inverter': str(row.get('warranty_inverter') or '').strip(),
                'regular_price': float(row['regular_price']) if row.get('regular_price') is not None else None,
                'cash_promo_price': float(row['cash_promo_price']) if row.get('cash_promo_price') is not None else None,
            })
    except (OperationalError, ProgrammingError):
        calculator_system_options = []

    return {
        'enable_floating_calculator': enabled,
        'calculator_default_meralco_rate': meralco_rate,
        'calculator_default_sun_peak_hours': sun_peak_hours,
        'calculator_default_vdrop_percent': vdrop_percent,
        'calculator_default_battery_health_drop_percent': battery_health_drop_percent,
        'calculator_system_options': calculator_system_options,
    }


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


def super_user_chat_access(request):
    user = getattr(request, 'user', None)
    preview = getattr(user, '_role_preview', None)
    preview_role_name = ((preview or {}).get('role_name') or '').strip().casefold()
    if preview is not None:
        has_access = bool(user and user.is_authenticated and preview_role_name == 'super users')
    else:
        has_access = bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.groups.filter(name='Super Users').exists()
            )
        )
    unread_count = 0
    if has_access:
        unread_query = SuperUserChatMessage.objects.filter(is_deleted=False).exclude(author=user)
        read_state = SuperUserChatReadState.objects.filter(user=user).first()
        if read_state and read_state.last_seen_message_id:
            unread_query = unread_query.filter(id__gt=read_state.last_seen_message_id)
        unread_count = unread_query.count()
    return {
        'can_access_super_user_chat': has_access,
        'super_user_chat_unread_count': unread_count,
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
        or url_name.startswith('consumables_')
        or url_name.startswith('accountability')
    )
    is_inventory_nav_active = url_name.startswith('inventory_')
    is_support_ticket_nav_active = url_name.startswith('support_ticket')
    is_crm_nav_active = url_name.startswith('crm_')
    is_human_resource_role = bool(
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact='Human Resource').exists()
        )
    )

    important_ticket_count = 0
    technical_action_required_count = 0
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

        can_view_crm = (
            _has_any_perm(request.user, CRM_VIEW_PERMISSIONS['dashboard'])
            or _has_any_perm(request.user, CRM_VIEW_PERMISSIONS['clients'])
            or _has_any_perm(request.user, CRM_VIEW_PERMISSIONS['sales'])
            or _has_any_perm(request.user, CRM_VIEW_PERMISSIONS['technicals'])
        )
        if can_view_crm:
            setting = CRMTechnicalNotificationSetting.objects.order_by('id').first()
            notify_days_before = getattr(setting, 'notify_days_before', 3)
            include_backlogs = bool(getattr(setting, 'include_backlogs', True))
            today = timezone.localdate()
            notify_before_date = today + timedelta(days=notify_days_before)
            actionable_q = (
                Q(installation_date__isnull=False, installation_date__lte=notify_before_date)
                & ~Q(installation_status__iexact='completed')
            )
            if include_backlogs:
                actionable_q = (
                    actionable_q
                    | Q(installation_status__iexact='back jobs')
                    | Q(installation_status__iexact='rescheduled')
                )

            actionable_q &= Q(sales_record__project_cost__isnull=False) & (
                Q(sales_record__sales_status__iexact='closed won') | Q(sales_record__sales_status__iexact='close won')
            )
            if not _has_any_perm(request.user, CRM_MANAGE_PERMISSIONS['technicals']):
                user_full_name = (request.user.get_full_name() or '').strip()
                user_username = (request.user.username or '').strip()
                ownership_filter = Q(sales_record__client__created_by=request.user)
                if user_full_name:
                    ownership_filter |= Q(sales_record__assigned_sales__icontains=user_full_name)
                if user_username:
                    ownership_filter |= Q(sales_record__assigned_sales__icontains=user_username)
                actionable_q &= ownership_filter
            technical_action_required_count = CRMTechnicalRecord.objects.filter(actionable_q).distinct().count()

    return {
        'is_crm_nav_active': is_crm_nav_active,
        'is_human_resource_role': is_human_resource_role,
        'is_finance_nav_active': is_finance_nav_active,
        'is_asset_tracker_nav_active': is_asset_tracker_nav_active,
        'is_inventory_nav_active': is_inventory_nav_active,
        'is_support_ticket_nav_active': is_support_ticket_nav_active,
        'important_ticket_count': important_ticket_count,
        'technical_action_required_count': technical_action_required_count,
    }
