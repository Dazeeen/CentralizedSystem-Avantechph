from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Q
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils import timezone

from .models import (
    CalculatorSetting,
    CalculatorImportRow,
    Notification,
    PrivateChatConversation,
    PrivateChatReadState,
    SuperUserChatMessage,
    SuperUserChatReadState,
    SupportTicket,
    CRMSalesRecord,
    CRMTechnicalRecord,
    CRMTechnicalNotificationSetting,
    CRMTechnicalTeam,
)
from .ticketing_services import (
    IMPORTANT_PRIORITY_VALUES,
    OPEN_TICKET_STATUS_VALUES,
    can_manage_support_tickets,
    effective_priority_filter,
)

CRM_ADMIN_PERMISSION = 'core.manage_crm_admin'
RECENT_PAGE_SESSION_KEY = 'recent_access_pages'
RECENT_PAGE_LIMIT = 8
SELECTED_ERP_MODULE_SESSION_KEY = 'selected_erp_module'

CRM_VIEW_PERMISSIONS = {
    'dashboard': (CRM_ADMIN_PERMISSION, 'core.view_crm_dashboard', 'core.view_client'),
    'clients': (CRM_ADMIN_PERMISSION, 'core.view_crm_clients_section', 'core.view_client'),
    'sales': (CRM_ADMIN_PERMISSION, 'core.view_crm_sales_section', 'core.view_client'),
    'technicals': (CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'),
    'aftersales': (CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'),
}

CRM_MANAGE_PERMISSIONS = {
    'clients': (CRM_ADMIN_PERMISSION, 'core.manage_crm_clients_section', 'core.change_client'),
    'sales': (CRM_ADMIN_PERMISSION, 'core.manage_crm_sales_section', 'core.change_client'),
    'technicals': (CRM_ADMIN_PERMISSION, 'core.manage_crm_technicals_section', 'core.change_client'),
}


PAGE_ACCESS_RULES = {
    'dashboard': {'label': 'Dashboard', 'audience': 'All signed-in users'},
    'attendance_page': {'label': 'Attendance', 'audience': 'All signed-in users'},
    'chats_page': {'label': 'Chats', 'audience': 'All signed-in users'},
    'timekeeping_page': {'label': 'Timekeeping', 'extra_roles': ['Human Resource'], 'audience': 'Human Resource role members and superusers'},
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
    'file_manager_setup': {'label': 'File Manager Setup', 'audience': 'Django superusers only'},
    'file_manager_browse_directories': {'label': 'File Manager Directory Browser', 'audience': 'Django superusers only'},
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
    'crm_dashboard': {'label': 'CRM Dashboard', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_dashboard', 'core.view_client']},
    'crm_clients': {'label': 'CRM Clients', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_clients_section', 'core.view_client']},
    'crm_sales': {'label': 'CRM Sales', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_sales_section', 'core.view_client']},
    'crm_technicals': {'label': 'CRM Technicals', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'crm_aftersales': {'label': 'CRM Aftersales', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'crm_aftersales_warranty': {'label': 'CRM Aftersales Warranty', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'crm_aftersales_concern': {'label': 'CRM Aftersales Concern', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'finance_dashboard': {
        'label': 'Accounting Dashboard',
        'perms': ['core.view_fundrequest', 'core.add_accountingrequest', 'core.view_accountingrequest', 'core.approve_accountingrequest'],
    },
    'accounting_requests': {
        'label': 'Accounting Requests',
        'perms': ['core.view_fundrequest', 'core.add_accountingrequest', 'core.view_accountingrequest', 'core.approve_accountingrequest'],
    },
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
    'procurement_dashboard': {'label': 'Procurement Dashboard', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_store': {'label': 'Manage Store', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_products': {'label': 'Manage Inventory', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_purchase_requests': {'label': 'Purchase Requests', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_job_requests': {'label': 'Job Requests', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_suppliers': {'label': 'Suppliers', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_supplier_management': {'label': 'Supplier Management', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_canvassing_quotations': {'label': 'Canvassing / Quotations', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_purchase_orders': {'label': 'Purchase Orders', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_po_receipts': {'label': 'PO Receipts', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_receiving_inspection': {'label': 'Receiving & Inspection', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_invoice_payment_coordination': {'label': 'Invoices', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_budgets': {'label': 'Budgets', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_notifications': {'label': 'Suggestions', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
    'procurement_reports': {'label': 'Reports', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
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


ERP_APP_DEFINITIONS = [
    {
        'key': 'attendance',
        'label': 'Attendance',
        'description': 'Daily in/out and attendance capture.',
        'url_name': 'attendance_page',
        'icon': 'calendar',
        'accent': '#20a4a6',
        'audience': 'all',
        'active_url_prefixes': ['attendance_'],
        'children': [
            {'label': 'Attendance', 'url_name': 'attendance_page', 'audience': 'all', 'active_url_prefixes': ['attendance_']},
        ],
    },
    {
        'key': 'chats',
        'label': 'Chats',
        'description': 'Private team conversations.',
        'url_name': 'chats_page',
        'icon': 'chat',
        'accent': '#7c5cdb',
        'audience': 'all',
        'badge_context': 'private_chat_unread_count',
        'active_url_prefixes': ['chats_'],
        'children': [
            {'label': 'Chats', 'url_name': 'chats_page', 'audience': 'all', 'active_url_prefixes': ['chats_']},
        ],
    },
    {
        'key': 'hr',
        'label': 'Human Resource',
        'description': 'Timekeeping and HR monitoring.',
        'url_name': 'timekeeping_page',
        'icon': 'people',
        'accent': '#ef8f35',
        'roles': ['Human Resource'],
        'active_url_prefixes': ['timekeeping_'],
        'children': [
            {'label': 'Timekeeping', 'url_name': 'timekeeping_page', 'roles': ['Human Resource'], 'active_url_prefixes': ['timekeeping_']},
        ],
    },
    {
        'key': 'crm',
        'label': 'CRM',
        'description': 'Clients, sales, technicals, and aftersales.',
        'url_name': 'crm_dashboard',
        'icon': 'crm',
        'accent': '#22a06b',
        'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_dashboard', 'core.view_crm_clients_section', 'core.view_crm_sales_section', 'core.view_crm_technicals_section', 'core.view_client'],
        'active_url_prefixes': ['crm_'],
        'active_url_names': ['procurement_job_requests'],
        'children': [
            {'label': 'Dashboard', 'url_name': 'crm_dashboard', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_dashboard', 'core.view_client']},
            {'label': 'Clients', 'url_name': 'crm_clients', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_clients_section', 'core.view_client'], 'active_url_prefixes': ['crm_client']},
            {'label': 'Sales', 'url_name': 'crm_sales', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_sales_section', 'core.view_client'], 'active_url_prefixes': ['crm_sales']},
            {'label': 'Technicals', 'url_name': 'crm_technicals', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'], 'active_url_prefixes': ['crm_technical'], 'active_url_names': ['procurement_job_requests']},
            {'label': 'Warranty', 'url_name': 'crm_aftersales_warranty', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'], 'active_url_prefixes': ['crm_aftersales_warranty']},
            {'label': 'Concern', 'url_name': 'crm_aftersales_concern', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'], 'active_url_prefixes': ['crm_aftersales_concern']},
        ],
        'badge_context': 'technical_action_required_count',
    },
    {
        'key': 'accounting',
        'label': 'Accounting',
        'description': 'Requests, liquidation, reimbursement, and summaries.',
        'url_name': 'finance_dashboard',
        'icon': 'money',
        'accent': '#cc8d1a',
        'perms': ['core.view_fundrequest', 'core.add_accountingrequest', 'core.view_accountingrequest', 'core.approve_accountingrequest'],
        'active_url_prefixes': ['finance_', 'fund_request', 'liquidation'],
        'active_url_names': ['accounting_requests'],
        'children': [
            {'label': 'Dashboard', 'url_name': 'finance_dashboard', 'perms': ['core.view_fundrequest', 'core.add_accountingrequest', 'core.view_accountingrequest', 'core.approve_accountingrequest']},
            {'label': 'Payment Request', 'url_name': 'fund_requests_list', 'perms': ['core.view_fundrequest'], 'active_url_prefixes': ['fund_request']},
            {'label': 'Accounting Requests', 'url_name': 'accounting_requests', 'perms': ['core.add_accountingrequest', 'core.view_accountingrequest', 'core.approve_accountingrequest']},
            {'label': 'Liquidation', 'url_name': 'liquidation_page', 'perms': ['core.view_liquidation', 'core.view_fundrequest'], 'active_url_prefixes': ['liquidation']},
            {'label': 'Reimbursement', 'url_name': 'finance_reimbursement', 'perms': ['core.view_fundrequest']},
            {'label': 'Summary Request', 'url_name': 'finance_summary_request', 'perms': ['core.view_fundrequest']},
        ],
    },
    {
        'key': 'procurement',
        'label': 'Procurement',
        'description': 'Dashboard, store, purchase, suppliers, inventory, and suggestions.',
        'url_name': 'procurement_dashboard',
        'icon': 'box',
        'accent': '#d65745',
        'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'],
        'active_url_prefixes': ['procurement_'],
        'children': [
            {'label': 'Dashboard', 'url_name': 'procurement_dashboard', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
            {'label': 'Manage Store', 'url_name': 'procurement_store', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
            {'label': 'Purchase Orders', 'url_name': 'procurement_purchase_orders', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'], 'active_url_names': ['procurement_purchase_requests']},
            {'label': 'PO Receipts', 'url_name': 'procurement_po_receipts', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'], 'active_url_names': ['procurement_receiving_inspection']},
            {'label': 'Invoices', 'url_name': 'procurement_invoice_payment_coordination', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
            {'label': 'Budgets', 'url_name': 'procurement_budgets', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
            {'label': 'Suppliers', 'url_name': 'procurement_suppliers', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client'], 'active_url_names': ['procurement_supplier_management', 'procurement_canvassing_quotations']},
            {'label': 'Manage Inventory', 'url_name': 'procurement_products', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
            {'label': 'Reports', 'url_name': 'procurement_reports', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
            {'label': 'Suggestions', 'url_name': 'procurement_notifications', 'perms': [CRM_ADMIN_PERMISSION, 'core.view_crm_technicals_section', 'core.view_client']},
        ],
    },
    {
        'key': 'forms',
        'label': 'Forms',
        'description': 'Reusable uploaded forms and internal documents.',
        'url_name': 'forms_list',
        'icon': 'form',
        'accent': '#4d7bd6',
        'staff_or_perms': ['core.view_assetaccountability', 'core.add_assetaccountability', 'core.change_assetaccountability', 'core.delete_assetaccountability'],
        'roles': ['Human Resource'],
        'active_url_prefixes': ['forms_'],
        'children': [
            {'label': 'Forms', 'url_name': 'forms_list', 'staff_or_perms': ['core.view_assetaccountability', 'core.add_assetaccountability', 'core.change_assetaccountability', 'core.delete_assetaccountability'], 'roles': ['Human Resource'], 'active_url_prefixes': ['forms_']},
        ],
    },
    {
        'key': 'calculator',
        'label': 'Calculator',
        'description': 'Solar and wattage computation tools.',
        'url_name': 'calculator_page',
        'icon': 'calculator',
        'accent': '#9b59b6',
        'staff_or_perms': ['core.view_assetaccountability', 'core.add_assetaccountability', 'core.change_assetaccountability', 'core.delete_assetaccountability'],
        'roles': ['Human Resource'],
        'active_url_names': ['calculator_page'],
        'children': [
            {'label': 'Calculator', 'url_name': 'calculator_page', 'staff_or_perms': ['core.view_assetaccountability', 'core.add_assetaccountability', 'core.change_assetaccountability', 'core.delete_assetaccountability'], 'roles': ['Human Resource']},
        ],
    },
    {
        'key': 'assets',
        'label': 'Asset Tracker',
        'description': 'Assets, accountability, consumables, and company accounts.',
        'url_name': 'assets_list',
        'icon': 'asset',
        'accent': '#39934d',
        'perms': ['core.view_assetitem', 'core.view_assettrackercategory', 'core.view_assetitemtype', 'core.view_consumableitem', 'core.view_consumableitemtype', 'core.view_consumablescategory', 'core.view_assetaccountability', 'core.view_companyinternetaccount', 'core.change_companyinternetaccount', 'core.add_companyinternetaccount'],
        'active_url_prefixes': ['assets_', 'consumables_', 'accountability'],
        'children': [
            {'label': 'Assets', 'url_name': 'assets_list', 'perms': ['core.view_assetitem'], 'active_url_prefixes': ['assets_item', 'assets_department', 'assets_tag']},
            {'label': 'Consumables', 'url_name': 'consumables_list', 'perms': ['core.view_consumableitem'], 'active_url_prefixes': ['consumables_']},
            {'label': 'Accountability', 'url_name': 'accountability_list', 'perms': ['core.view_assetaccountability'], 'active_url_prefixes': ['accountability']},
            {'label': 'Internet Accounts', 'url_name': 'assets_company_accounts', 'perms': ['core.view_companyinternetaccount', 'core.change_companyinternetaccount', 'core.add_companyinternetaccount']},
        ],
    },
    {
        'key': 'warehouse',
        'label': 'Warehouse',
        'description': 'Inventory dashboard, reporting, support, and settings.',
        'url_name': 'inventory_dashboard_page',
        'icon': 'warehouse',
        'accent': '#2f80a8',
        'perms': ['core.view_assetitem'],
        'active_url_prefixes': ['inventory_'],
        'children': [
            {'label': 'Dashboard', 'url_name': 'inventory_dashboard_page', 'perms': ['core.view_assetitem']},
            {'label': 'Inventory', 'url_name': 'inventory_page', 'perms': ['core.view_assetitem']},
            {'label': 'Orders', 'url_name': 'inventory_orders_page', 'perms': ['core.view_assetitem']},
            {'label': 'Purchase', 'url_name': 'inventory_purchase_page', 'perms': ['core.view_assetitem']},
            {'label': 'Reporting', 'url_name': 'inventory_reporting_page', 'perms': ['core.view_assetitem']},
            {'label': 'Support', 'url_name': 'inventory_support_page', 'perms': ['core.view_assetitem']},
            {'label': 'Settings', 'url_name': 'inventory_settings_page', 'perms': ['core.view_assetitem']},
        ],
    },
    {
        'key': 'users',
        'label': 'Users',
        'description': 'Users, roles, and login access controls.',
        'url_name': 'users_list',
        'icon': 'users',
        'accent': '#5865c8',
        'perms': ['auth.view_user'],
        'active_url_prefixes': ['users_', 'roles_'],
        'active_url_names': ['support_lockout_center'],
        'children': [
            {'label': 'Users', 'url_name': 'users_list', 'perms': ['auth.view_user'], 'active_url_prefixes': ['users_']},
            {'label': 'Roles', 'url_name': 'roles_list', 'perms': ['auth.view_group'], 'active_url_prefixes': ['roles_']},
            {'label': 'Login Security', 'url_name': 'support_lockout_center', 'perms': ['axes.view_accessattempt']},
        ],
    },
    {
        'key': 'files',
        'label': 'File Manager',
        'description': 'Managed company files and folders.',
        'url_name': 'file_manager_list',
        'icon': 'folder',
        'accent': '#c49a21',
        'perms': ['core.view_managedfilenode'],
        'active_url_prefixes': ['file_manager_'],
        'children': [
            {'label': 'File Manager', 'url_name': 'file_manager_list', 'perms': ['core.view_managedfilenode'], 'active_url_prefixes': ['file_manager_']},
        ],
    },
    {
        'key': 'support',
        'label': 'Support Tickets',
        'description': 'Issue reports and support queue.',
        'url_name': 'support_tickets_list',
        'icon': 'support',
        'accent': '#e05f7a',
        'audience': 'all',
        'badge_context': 'important_ticket_count',
        'active_url_prefixes': ['support_ticket'],
        'children': [
            {'label': 'Tickets', 'url_name': 'support_tickets_list', 'audience': 'all', 'active_url_prefixes': ['support_ticket']},
            {'label': 'Create Ticket', 'url_name': 'support_ticket_create', 'audience': 'all'},
        ],
    },
    {
        'key': 'development',
        'label': 'Development',
        'description': 'Feedback hub and patch notes.',
        'url_name': 'development_hub',
        'icon': 'code',
        'accent': '#64748b',
        'audience': 'all',
        'active_url_prefixes': ['development_'],
        'children': [
            {'label': 'Development Hub', 'url_name': 'development_hub', 'audience': 'all'},
            {'label': 'Patch Notes', 'url_name': 'development_patch_notes', 'audience': 'all', 'active_url_prefixes': ['development_patch']},
        ],
    },
    {
        'key': 'system',
        'label': 'System',
        'description': 'Backups, activity logs, database tools, and admin chat.',
        'url_name': 'system_hub',
        'fallback_url_names': ['super_user_chat', 'activity_logs'],
        'icon': 'system',
        'accent': '#51606f',
        'perms': ['core.view_databasefile', 'core.add_databasefile', 'core.change_databasefile', 'core.delete_databasefile', 'core.view_activitylog'],
        'special_access': 'system_tools',
        'badge_context': 'super_user_chat_unread_count',
        'active_url_prefixes': ['system_'],
        'active_url_names': ['activity_logs', 'super_user_chat', 'super_user_chat_delete'],
        'children': [
            {'label': 'System Hub', 'url_name': 'system_hub', 'perms': ['core.view_databasefile', 'core.add_databasefile', 'core.change_databasefile', 'core.delete_databasefile'], 'active_url_prefixes': ['system_backup', 'system_database']},
            {'label': 'Activity Logs', 'url_name': 'activity_logs', 'perms': ['core.view_activitylog']},
            {'label': 'Super User Chat', 'url_name': 'super_user_chat', 'roles': ['Super Users'], 'active_url_prefixes': ['super_user_chat']},
        ],
    },
]


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


def _is_in_any_role(user, role_names):
    if not role_names:
        return False
    if user.is_superuser:
        return True
    normalized_role_names = {role_name.casefold() for role_name in role_names}
    preview = getattr(user, '_role_preview', None)
    preview_role_name = ((preview or {}).get('role_name') or '').strip().casefold()
    if preview is not None:
        return preview_role_name in normalized_role_names
    return any(group_name.casefold() in normalized_role_names for group_name in user.groups.values_list('name', flat=True))


def _can_access_erp_item(user, item):
    if not user or not user.is_authenticated:
        return False
    if item.get('audience') == 'all':
        return True
    if user.is_superuser:
        return True
    if item.get('perms') and _has_any_perm(user, item['perms']):
        return True
    if item.get('special_access') == 'system_tools' and _is_in_any_role(user, ['Super Users']):
        return True
    if item.get('roles') and _is_in_any_role(user, item['roles']):
        return True
    staff_or_perms = item.get('staff_or_perms') or []
    if staff_or_perms and (user.is_staff or _has_any_perm(user, staff_or_perms)):
        return True
    return False


def _reverse_url_name(url_name):
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return ''


def _system_tools_url_name(user):
    database_permissions = [
        'core.view_databasefile',
        'core.add_databasefile',
        'core.change_databasefile',
        'core.delete_databasefile',
    ]
    if user.is_superuser or _has_any_perm(user, database_permissions):
        return 'system_hub'
    if _is_in_any_role(user, ['Super Users']):
        return 'super_user_chat'
    return 'activity_logs'


def _matches_url_name(item, url_name):
    if not url_name:
        return False
    if url_name == item.get('url_name'):
        return True
    if url_name in (item.get('active_url_names') or []):
        return True
    return any(url_name.startswith(prefix) for prefix in (item.get('active_url_prefixes') or []))


def _build_erp_apps(user, counts=None, current_url_name=''):
    counts = counts or {}
    apps = []
    for definition in ERP_APP_DEFINITIONS:
        if not _can_access_erp_item(user, definition):
            continue

        url_name = definition['url_name']
        if definition.get('special_access') == 'system_tools':
            url_name = _system_tools_url_name(user)

        url = _reverse_url_name(url_name)
        if not url:
            for fallback_url_name in definition.get('fallback_url_names') or []:
                url = _reverse_url_name(fallback_url_name)
                if url:
                    break
        if not url:
            continue

        children = []
        for child in definition.get('children') or []:
            if not _can_access_erp_item(user, child):
                continue
            child_url = _reverse_url_name(child['url_name'])
            if child_url:
                children.append({
                    'label': child['label'],
                    'url': child_url,
                    'url_name': child['url_name'],
                    'is_active': _matches_url_name(child, current_url_name),
                })

        badge_count = 0
        badge_context = definition.get('badge_context')
        if badge_context:
            try:
                badge_count = int(counts.get(badge_context) or 0)
            except (TypeError, ValueError):
                badge_count = 0

        apps.append({
            'key': definition['key'],
            'label': definition['label'],
            'description': definition.get('description', ''),
            'url': url,
            'select_url': f'{url}?system={definition["key"]}',
            'url_name': url_name,
            'icon': definition.get('icon', 'app'),
            'accent': definition.get('accent', '#198754'),
            'children': children,
            'child_count': len(children),
            'badge_count': badge_count,
            'is_active': _matches_url_name(definition, current_url_name) or any(child['is_active'] for child in children),
        })
    return apps


def _active_erp_module(apps, selected_key=''):
    for app in apps:
        if app.get('is_active'):
            return app
    if selected_key:
        for app in apps:
            if app.get('key') == selected_key:
                return app
    return None


def _selected_erp_module_key(request, apps, url_name):
    selected_key = (request.GET.get('system') or '').strip()
    valid_keys = {app.get('key') for app in apps}
    if selected_key in valid_keys:
        request.session[SELECTED_ERP_MODULE_SESSION_KEY] = selected_key
        request.session.modified = True
        return selected_key

    active_app = next((app for app in apps if app.get('is_active')), None)
    if active_app:
        request.session[SELECTED_ERP_MODULE_SESSION_KEY] = active_app['key']
        request.session.modified = True
        return active_app['key']

    if url_name == 'dashboard':
        request.session.pop(SELECTED_ERP_MODULE_SESSION_KEY, None)
        return ''

    saved_key = request.session.get(SELECTED_ERP_MODULE_SESSION_KEY, '')
    return saved_key if saved_key in valid_keys else ''


def _track_recent_access(request):
    user = getattr(request, 'user', None)
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = getattr(resolver_match, 'url_name', '') or ''
    recent_pages = request.session.get(RECENT_PAGE_SESSION_KEY, [])

    if (
        user
        and user.is_authenticated
        and request.method == 'GET'
        and url_name
        and url_name != 'dashboard'
        and url_name in PAGE_ACCESS_RULES
    ):
        label = PAGE_ACCESS_RULES[url_name].get('label') or url_name.replace('_', ' ').title()
        page = {
            'label': label,
            'url': request.get_full_path(),
            'url_name': url_name,
        }
        recent_pages = [item for item in recent_pages if item.get('url') != page['url']]
        recent_pages.insert(0, page)
        recent_pages = recent_pages[:RECENT_PAGE_LIMIT]
        request.session[RECENT_PAGE_SESSION_KEY] = recent_pages
        request.session.modified = True

    return recent_pages[:RECENT_PAGE_LIMIT]


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


def welcome_responsibility_reminders(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'welcome_reminders_modal': None}

    should_show = bool(request.session.pop('show_welcome_reminders_modal', False))
    if not should_show:
        return {'welcome_reminders_modal': None}

    today = timezone.localdate()
    due_until = today + timedelta(days=7)
    display_name = user.get_full_name() or user.username
    reminders = []

    try:
        can_view_sales = _has_any_perm(user, CRM_VIEW_PERMISSIONS['sales'])
        can_manage_sales = _has_any_perm(user, CRM_MANAGE_PERMISSIONS['sales'])
        if can_view_sales:
            sales_q = (
                CRMSalesRecord.objects
                .select_related('client')
                .filter(ocular_date__isnull=False, ocular_date__lte=due_until)
                .exclude(sales_status__iexact='closed won')
                .exclude(sales_status__iexact='closed lost')
                .order_by('ocular_date', 'client__last_name')
            )
            if not can_manage_sales and not user.is_superuser:
                name_tokens = {
                    (user.get_full_name() or '').strip().lower(),
                    (user.username or '').strip().lower(),
                    (user.email or '').strip().lower(),
                }
                sales_filter = Q()
                for token in {token for token in name_tokens if token}:
                    sales_filter |= Q(assigned_sales__icontains=token)
                sales_q = sales_q.filter(sales_filter) if sales_filter else sales_q.none()
            for record in sales_q[:8]:
                client = record.client
                client_name = f'{client.last_name}, {client.first_name}' if getattr(record, 'client_id', None) else f'Sales #{record.id}'
                reminders.append({
                    'category': 'Ocular',
                    'title': client_name,
                    'detail': f'Survey schedule on {record.ocular_date:%b %d, %Y}',
                    'date': record.ocular_date,
                    'urgency': 'Today' if record.ocular_date == today else f'{max((record.ocular_date - today).days, 0)} day(s)',
                    'link': reverse('crm_sales'),
                })

        can_view_technicals = _has_any_perm(user, CRM_VIEW_PERMISSIONS['technicals'])
        can_manage_technicals = _has_any_perm(user, CRM_MANAGE_PERMISSIONS['technicals'])
        if can_view_technicals:
            technical_q = (
                CRMTechnicalRecord.objects
                .select_related('sales_record__client')
                .filter(installation_date__isnull=False, installation_date__lte=due_until)
                .exclude(installation_status__iexact='completed')
                .order_by('installation_date', 'installation_time')
            )
            if not can_manage_technicals and not user.is_superuser:
                team_names = list(
                    CRMTechnicalTeam.objects
                    .filter(members=user)
                    .exclude(name__isnull=True)
                    .exclude(name__exact='')
                    .values_list('name', flat=True)
                    .distinct()
                )
                team_q = Q()
                for team_name in team_names:
                    team_q |= Q(team_assigned__iexact=team_name)
                technical_q = technical_q.filter(team_q) if team_q else technical_q.none()
            for tech in technical_q[:10]:
                sales_record = tech.sales_record
                client = sales_record.client if sales_record and sales_record.client_id else None
                client_name = f'{client.last_name}, {client.first_name}' if client else f'Technical #{tech.id}'
                schedule_text = tech.installation_date.strftime('%b %d, %Y')
                if tech.installation_time:
                    schedule_text += f' {tech.installation_time:%I:%M %p}'
                reminders.append({
                    'category': 'Technical',
                    'title': client_name,
                    'detail': f'Installation schedule on {schedule_text}',
                    'date': tech.installation_date,
                    'urgency': 'Today' if tech.installation_date == today else f'{max((tech.installation_date - today).days, 0)} day(s)',
                    'link': reverse('crm_technicals'),
                })
    except (OperationalError, ProgrammingError):
        reminders = []

    reminders = sorted(reminders, key=lambda item: (item.get('date') or due_until, item.get('category', '')))[:10]
    return {
        'welcome_reminders_modal': {
            'display_name': display_name,
            'reminders': reminders,
            'has_reminders': bool(reminders),
        }
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


def private_chat_summary(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'private_chat_unread_count': 0}

    unread_count = 0
    conversations = PrivateChatConversation.objects.filter(Q(participant_one=user) | Q(participant_two=user)).distinct()
    for conversation in conversations:
        read_state = PrivateChatReadState.objects.filter(conversation=conversation, user=user).first()
        last_read_id = int(read_state.last_read_message_id or 0) if read_state else 0
        unread_count += conversation.messages.exclude(sender=user).filter(id__gt=last_read_id).count()
    return {'private_chat_unread_count': unread_count}


def finance_navigation_state(request):
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = getattr(resolver_match, 'url_name', '') or ''
    is_finance_nav_active = (
        url_name.startswith('finance_')
        or url_name == 'accounting_requests'
        or url_name.startswith('fund_request')
        or url_name.startswith('liquidation')
    )
    is_asset_tracker_nav_active = (
        url_name.startswith('assets_')
        or url_name.startswith('consumables_')
        or url_name.startswith('accountability')
    )
    is_inventory_nav_active = url_name.startswith('inventory_')
    is_procurement_nav_active = url_name.startswith('procurement_') and url_name != 'procurement_job_requests'
    is_support_ticket_nav_active = url_name.startswith('support_ticket')
    is_crm_nav_active = url_name.startswith('crm_') or url_name == 'procurement_job_requests'
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
            or _has_any_perm(request.user, CRM_VIEW_PERMISSIONS['aftersales'])
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

    counts = {
        'important_ticket_count': important_ticket_count,
        'technical_action_required_count': technical_action_required_count,
        'private_chat_unread_count': private_chat_summary(request).get('private_chat_unread_count', 0),
        'super_user_chat_unread_count': super_user_chat_access(request).get('super_user_chat_unread_count', 0),
    }
    erp_app_modules = _build_erp_apps(request.user, counts, current_url_name=url_name)
    selected_erp_module_key = _selected_erp_module_key(request, erp_app_modules, url_name)
    active_erp_module = _active_erp_module(erp_app_modules, selected_key=selected_erp_module_key)

    return {
        'is_crm_nav_active': is_crm_nav_active,
        'is_human_resource_role': is_human_resource_role,
        'is_finance_nav_active': is_finance_nav_active,
        'is_asset_tracker_nav_active': is_asset_tracker_nav_active,
        'is_inventory_nav_active': is_inventory_nav_active,
        'is_procurement_nav_active': is_procurement_nav_active,
        'is_support_ticket_nav_active': is_support_ticket_nav_active,
        'important_ticket_count': important_ticket_count,
        'technical_action_required_count': technical_action_required_count,
        'erp_app_modules': erp_app_modules,
        'active_erp_module': active_erp_module,
        'selected_erp_module_key': selected_erp_module_key,
        'erp_home_app': {
            'label': 'App Menu',
            'icon': 'app',
            'accent': '#198754',
        },
        'recent_access_pages': _track_recent_access(request),
    }
