import shutil
import tempfile
import zipfile
from io import BytesIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import OperationalError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from . import system_backup_services, system_views, views
from .forms import AssetItemForm, FundRequestForm, RoleForm, prepare_image_upload
from .permission_catalog import BASIC_ROLE_PERMISSION_KEYS, get_basic_role_permission_ids
from .models import (
    AssetAccountability,
    AssetAccountabilityFormBatch,
    AssetAccountabilityTemplate,
    AssetDepartment,
    AssetItem,
    AssetItemType,
    ActivityLog,
    FundRequest,
    FundRequestLineItem,
    FundRequestTemplate,
    ManagedFileNode,
    ManagedFilePermission,
    SuperUserChatMessage,
    SuperUserChatReadState,
    SystemBackupSchedule,
    SupportTicket,
)


def _build_docx_template_bytes(text):
    output = BytesIO()
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>'
        f'{text}'
        '</w:t></w:r></w:p></w:body></w:document>'
    )
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types></Types>')
        archive.writestr('word/document.xml', document_xml)
    return output.getvalue()


class RoleFormBasicAccessTests(TestCase):
    def test_create_role_defaults_to_basic_access_permissions(self):
        form = RoleForm()
        selected_ids = {str(value) for value in form.initial.get('permissions', [])}
        expected_ids = {str(value) for value in get_basic_role_permission_ids()}

        self.assertTrue(expected_ids)
        self.assertEqual(selected_ids, expected_ids)

        for app_label, model, codename in BASIC_ROLE_PERMISSION_KEYS:
            self.assertTrue(
                Permission.objects.filter(
                    content_type__app_label=app_label,
                    content_type__model=model,
                    codename=codename,
                ).exists(),
                f'Missing basic role permission: {app_label}.{codename}',
            )

    def test_edit_role_uses_existing_permissions_not_basic_access_preset(self):
        role = Group.objects.create(name='Custom Role')
        custom_permission = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='fundrequest',
            codename='view_fundrequest',
        )
        role.permissions.set([custom_permission])

        form = RoleForm(instance=role)
        selected_values = form._selected_field_values('permissions')

        self.assertEqual(selected_values, {str(custom_permission.pk)})

    def test_role_access_preview_includes_default_and_permission_pages(self):
        role = Group.objects.create(name='Finance Viewer')
        role.permissions.add(
            Permission.objects.get(
                content_type__app_label='core',
                content_type__model='fundrequest',
                codename='view_fundrequest',
            )
        )

        preview = views._build_role_access_preview(role)
        accessible_labels = {page['label'] for page in preview['accessible_pages']}
        unavailable_labels = {page['label'] for page in preview['unavailable_pages']}

        self.assertIn('Dashboard', accessible_labels)
        self.assertIn('Finance Dashboard', accessible_labels)
        self.assertIn('Payment Request', accessible_labels)
        self.assertIn('Reimbursement', accessible_labels)
        self.assertIn('Summary Request', accessible_labels)
        self.assertNotIn('Finance Dashboard', unavailable_labels)

    def test_roles_list_renders_preview_button(self):
        role = Group.objects.create(name='Preview Role')
        viewer = get_user_model().objects.create_user(username='role-viewer', password='password')
        viewer.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='auth',
                content_type__model='group',
                codename='view_group',
            )
        )

        self.client.force_login(viewer)
        response = self.client.get(reverse('roles_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preview as Preview Role')

    def test_role_preview_browses_with_selected_role_permissions(self):
        role = Group.objects.create(name='Finance Preview')
        role.permissions.add(
            Permission.objects.get(
                content_type__app_label='core',
                content_type__model='fundrequest',
                codename='view_fundrequest',
            )
        )
        admin = get_user_model().objects.create_superuser(
            username='preview-admin',
            email='preview-admin@example.com',
            password='password',
        )

        self.client.force_login(admin)
        response = self.client.post(reverse('roles_preview_start', args=[role.id]))

        self.assertRedirects(response, reverse('dashboard'))

        finance_response = self.client.get(reverse('finance_dashboard'))
        self.assertEqual(finance_response.status_code, 200)
        self.assertContains(finance_response, 'Previewing as Finance Preview')
        self.assertContains(finance_response, 'Finance')
        self.assertNotContains(finance_response, 'Users</span>')

        users_response = self.client.get(reverse('users_list'))
        self.assertRedirects(users_response, reverse('dashboard'))

        stop_response = self.client.post(reverse('roles_preview_stop'), follow=True)
        self.assertRedirects(stop_response, reverse('dashboard'))
        self.assertContains(stop_response, 'Stopped previewing as Finance Preview')
        self.assertNotContains(stop_response, 'Previewing as Finance Preview')

        roles_response = self.client.get(reverse('roles_list'))
        self.assertEqual(roles_response.status_code, 200)

    def test_role_preview_blocks_support_ticket_submission(self):
        role = Group.objects.create(name='Sales Preview')
        admin = get_user_model().objects.create_superuser(
            username='ticket-preview-admin',
            email='ticket-preview-admin@example.com',
            password='password',
        )

        self.client.force_login(admin)
        self.client.post(reverse('roles_preview_start', args=[role.id]))
        response = self.client.post(
            reverse('support_ticket_create'),
            {
                'title': 'Preview ticket',
                'category': 'access',
                'description': 'This should not be saved during preview.',
                'requested_priority': 'medium',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertFalse(SupportTicket.objects.filter(title='Preview ticket').exists())

    def test_role_preview_uses_preview_role_for_super_user_chat_access(self):
        super_group = Group.objects.create(name='Super Users')
        role = Group.objects.create(name='Activity Viewer')
        role.permissions.add(
            Permission.objects.get(
                content_type__app_label='core',
                content_type__model='activitylog',
                codename='view_activitylog',
            )
        )
        admin = get_user_model().objects.create_superuser(
            username='system-preview-admin',
            email='system-preview-admin@example.com',
            password='password',
        )
        admin.groups.add(super_group)

        self.client.force_login(admin)
        self.client.post(reverse('roles_preview_start', args=[role.id]))
        chat_response = self.client.get(reverse('super_user_chat'))
        system_response = self.client.get(reverse('system_hub'))

        self.assertRedirects(chat_response, reverse('dashboard'))
        self.assertRedirects(system_response, reverse('activity_logs'))


class SuperUserChatReadStateTests(TestCase):
    def test_role_preview_does_not_mark_super_user_chat_seen(self):
        user = get_user_model().objects.create_superuser(username='chat-admin', password='password')
        SuperUserChatMessage.objects.create(author=user, message='Hello')
        user._role_preview = {
            'role_id': 1,
            'role_name': 'Super Users',
            'permission_names': set(),
        }

        system_views._mark_super_user_chat_seen(user)

        self.assertFalse(SuperUserChatReadState.objects.filter(user=user).exists())

    def test_database_lock_does_not_crash_super_user_chat_seen_marker(self):
        user = get_user_model().objects.create_superuser(username='chat-admin', password='password')
        SuperUserChatMessage.objects.create(author=user, message='Hello')

        with patch.object(
            SuperUserChatReadState.objects,
            'update_or_create',
            side_effect=OperationalError('database is locked'),
        ):
            system_views._mark_super_user_chat_seen(user)

        self.assertFalse(SuperUserChatReadState.objects.filter(user=user).exists())


class SystemBackupActivityLogTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp(prefix='backup-activity-test-media-')

    def tearDown(self):
        shutil.rmtree(self._media_root, ignore_errors=True)

    def test_manual_backup_run_records_backup_activity_category(self):
        admin = get_user_model().objects.create_superuser(username='backup-admin', password='password')
        self.client.force_login(admin)
        SystemBackupSchedule.objects.create(
            name='Manual Backup Schedule',
            include_logs=False,
            include_docs=False,
            include_media=False,
            include_database=False,
            include_static=False,
            include_templates=True,
        )

        with self.settings(MEDIA_ROOT=self._media_root):
            response = self.client.post(reverse('system_backup_run_now'))

        self.assertRedirects(response, reverse('system_hub'))
        log = ActivityLog.objects.get(category='backup', action='create')
        self.assertEqual(log.actor, admin)
        self.assertIn('Manual system backup created', log.summary)
        self.assertEqual(log.metadata['trigger'], 'manual')
        self.assertIn('templates', log.metadata['included_scopes'])

    def test_scheduled_backup_run_records_backup_activity_category(self):
        now = timezone.localtime(timezone.now())
        SystemBackupSchedule.objects.create(
            name='Scheduled Backup Schedule',
            is_enabled=True,
            cron_minute=now.minute,
            include_logs=False,
            include_docs=False,
            include_media=False,
            include_database=False,
            include_static=False,
            include_templates=True,
        )

        with self.settings(MEDIA_ROOT=self._media_root):
            created = system_backup_services.run_due_system_backups(now=now)

        self.assertEqual(len(created), 1)
        log = ActivityLog.objects.get(category='backup', action='create')
        self.assertIsNone(log.actor)
        self.assertIn('Scheduled system backup created', log.summary)
        self.assertEqual(log.metadata['trigger'], 'scheduled')
        self.assertEqual(log.target_label, created[0].backup_name)


class AssetItemParentTypeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='asset-admin', password='password')
        self.department = AssetDepartment.objects.create(name='QA Assets', is_default=True)
        self.item_type = AssetItemType.objects.create(name='Monitor', code='monitor', prefix='MON', is_active=True)
        self.parent_item = AssetItem.objects.create(
            department=self.department,
            item_name='Monitor',
            item_type='monitor',
            code_prefix='MON',
            stock_quantity=0,
            low_stock_threshold=1,
        )

    def test_asset_item_form_locks_parent_to_matching_item_type(self):
        form = AssetItemForm(
            data={
                'department': self.department.id,
                'parent_item': '',
                'item_name': '27 inch Monitor',
                'item_type': 'monitor',
                'code_prefix': '',
                'specification': '',
                'note': '',
                'stock_quantity': '1',
                'low_stock_threshold': '1',
                'is_active': 'on',
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['parent_item'], self.parent_item)

    def test_item_type_parent_item_is_created_when_missing(self):
        mouse_type = AssetItemType.objects.create(name='Mouse', code='mouse', prefix='MSE', is_active=True)

        parent_item, created = views._ensure_asset_type_parent_item(mouse_type, created_by=self.user)

        self.assertTrue(created)
        self.assertEqual(parent_item.item_name, 'Mouse')
        self.assertEqual(parent_item.item_type, 'mouse')
        self.assertEqual(parent_item.department, views._get_default_asset_department())
        self.assertEqual(parent_item.created_by, self.user)
        self.assertTrue(parent_item.item_code.startswith('MSE'))


class PaymentRequestPlaceholderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='requester', password='password')

    def test_supplier_and_fuel_placeholders_render_when_enabled(self):
        request = FundRequest.objects.create(
            requester_name='Requester One',
            department='Operations',
            branch='Alabang',
            created_by=self.user,
            request_metadata={
                'supplier_details_known': True,
                'supplier_store_name': 'Sample Hardware',
                'contact_person_details': 'Maria Santos 0917-000-0000',
                'line_items': [
                    {
                        'row_type': 'gas_fuel',
                        'vehicle_to_be_used': 'Service Van',
                        'plate_number': 'ABC 1234',
                        'current_odometer_reading': '12000 km',
                        'estimated_distance_to_travel': '35 km',
                        'purpose_of_travel': 'Pickup materials',
                    }
                ],
            },
        )
        FundRequestLineItem.objects.create(
            fund_request=request,
            entry_date=request.request_date,
            particulars='Gas / Fuel | Fuel or gas expense',
            amount='1500.00',
        )

        placeholders = views._build_fund_request_template_placeholders(request)

        self.assertIn('Service Van', placeholders['{{ fuel_gas_details }}'])
        self.assertIn('ABC 1234', placeholders['{{ fuel-gas_details }}'])
        self.assertIn('Sample Hardware', placeholders['{{ supplier_service_details }}'])
        self.assertIn('Maria Santos', placeholders['{{ supplier-server-details }}'])

    def test_supplier_and_fuel_placeholders_are_empty_when_disabled(self):
        request = FundRequest.objects.create(
            requester_name='Requester Two',
            department='Operations',
            branch='Alabang',
            created_by=self.user,
            request_metadata={
                'supplier_details_known': False,
                'supplier_store_name': 'Should Not Render',
                'contact_person_details': 'Should Not Render',
                'line_items': [],
            },
        )

        placeholders = views._build_fund_request_template_placeholders(request)

        self.assertEqual(placeholders['{{ fuel_gas_details }}'], '')
        self.assertEqual(placeholders['{{ fuel-gas_details }}'], '')
        self.assertEqual(placeholders['{{ supplier_service_details }}'], '')
        self.assertEqual(placeholders['{{ supplier-server-details }}'], '')

    def test_planned_expense_dynamic_row_fields_use_metadata(self):
        request = FundRequest.objects.create(
            requester_name='Requester Three',
            department='Operations',
            branch='Alabang',
            created_by=self.user,
            request_metadata={
                'mode_of_release': 'cash',
                'line_items': [
                    {
                        'category': 'Materials/Purchases',
                        'description': 'PVC pipe',
                        'quantity': '4',
                        'unit_of_measurement': 'pcs',
                        'estimated_cost': '2500',
                    }
                ],
            },
        )
        FundRequestLineItem.objects.create(
            fund_request=request,
            entry_date=request.request_date,
            particulars='Materials/Purchases | PVC pipe | Qty 4 pcs | PHP 2,500.00',
            amount='2500.00',
        )

        placeholders = views._build_fund_request_template_placeholders(request)
        line_items = views._build_fund_request_line_items_context(request)

        self.assertEqual(placeholders['{{ date_needed }}'], placeholders['{{ request_date }}'])
        self.assertEqual(placeholders['{{ payment_mode }}'], 'Cash')
        self.assertEqual(placeholders['{{ ctrl_no }}'], '')
        self.assertEqual(placeholders['{{ item_1_category }}'], 'Materials/Purchases')
        self.assertEqual(placeholders['{{ item_1_description }}'], 'PVC pipe')
        self.assertEqual(placeholders['{{ item_1_quantity }}'], '4')
        self.assertEqual(placeholders['{{ item_1_uom }}'], 'pcs')
        self.assertEqual(placeholders['{{ item_1_estimated_cost }}'], '2,500.00')
        self.assertEqual(placeholders['{{ line_1_category }}'], 'Materials/Purchases')
        self.assertEqual(placeholders['{{ line_1_description }}'], 'PVC pipe')
        self.assertEqual(placeholders['{{ line_1_quantity }}'], '4')
        self.assertEqual(placeholders['{{ line_1_uom }}'], 'pcs')
        self.assertEqual(placeholders['{{ line_1_estimated_cost }}'], '2,500.00')
        self.assertEqual(placeholders['{{ line_2_category }}'], '')
        self.assertEqual(placeholders['{{ line_20_estimated_cost }}'], '')
        self.assertEqual(line_items[0]['category'], 'Materials/Purchases')
        self.assertEqual(line_items[0]['description'], 'PVC pipe')
        self.assertEqual(line_items[0]['quantity'], '4')
        self.assertEqual(line_items[0]['uom'], 'pcs')
        self.assertEqual(line_items[0]['estimated_cost'], '2,500.00')

    def test_xlsx_line_item_block_repeats_whole_b20_to_f20_row(self):
        content = (
            '<worksheet><sheetData>'
            '<row r="20">'
            '<c r="B20"><v>{{#line_items}}{{ category }}</v></c>'
            '<c r="C20"><v>{{ description }}</v></c>'
            '<c r="D20"><v>{{ quantity }}</v></c>'
            '<c r="E20"><v>{{ uom }}</v></c>'
            '<c r="F20"><v>{{ estimated_cost }}{{/line_items}}</v></c>'
            '</row>'
            '</sheetData></worksheet>'
        )
        line_items = [
            {'category': 'Materials/Purchases', 'description': 'PVC pipe', 'quantity': '4', 'uom': 'pcs', 'estimated_cost': '2,500.00'},
            {'category': 'Gas/Fuel', 'description': 'Diesel', 'quantity': '1', 'uom': 'lot', 'estimated_cost': '1,000.00'},
        ]

        rendered = views._replace_placeholders_in_text(content, {}, line_items=line_items, extension='.xlsx')

        self.assertIn('r="20"', rendered)
        self.assertIn('r="21"', rendered)
        self.assertIn('r="B20"', rendered)
        self.assertIn('r="B21"', rendered)
        self.assertIn('Materials/Purchases', rendered)
        self.assertIn('Gas/Fuel', rendered)
        self.assertNotIn('{{#line_items}}', rendered)
        self.assertNotIn('{{/line_items}}', rendered)

    def test_payment_request_placeholder_guide_is_cleaned_for_current_template(self):
        visible_placeholders = [
            item['placeholder']
            for item in views._build_fund_request_template_placeholder_guide()
        ]

        self.assertEqual(
            visible_placeholders,
            [
                '{{ ctrl_no }}',
                '{{ request_date }}',
                '{{ requester_name }}',
                '{{ department }}',
                '{{ purpose_of_request }}',
                '{{ total_amount_php }}',
                '{{ date_needed }}',
                '{{ payment_mode }}',
                '{{ line_1_category }}',
                '{{ line_1_description }}',
                '{{ line_1_quantity }}',
                '{{ line_1_uom }}',
                '{{ line_1_estimated_cost }}',
                '{{#line_items}} ... {{/line_items}}',
                '{{ fuel-gas_details }}',
                '{{ supplier-server-details }}',
            ],
        )

    def test_payment_request_form_defaults_blank_quantity_to_one(self):
        image_bytes = BytesIO()
        Image.new('RGB', (2, 2), 'white').save(image_bytes, format='JPEG')
        form = FundRequestForm(
            data={
                'requester_name': 'Requester Four',
                'request_date': '2026-05-04',
                'department': 'Operations',
                'branch': 'Alabang',
                'purpose_of_request': 'Materials',
                'mode_of_release': 'cash',
                'supplier_details_known': 'no',
                'line_items_payload': json.dumps(
                    [
                        {
                            'row_type': 'material',
                            'category': 'Materials/Purchases',
                            'description': 'PVC pipe',
                            'quantity': '',
                            'unit_of_measurement': 'pcs',
                            'estimated_cost': '2500',
                        }
                    ]
                ),
            },
            files={
                'request_images': SimpleUploadedFile('proof.jpg', image_bytes.getvalue(), content_type='image/jpeg'),
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        line_item = form.get_line_items()[0]
        self.assertEqual(line_item['quantity'], 1)
        self.assertIn('Qty 1 pcs', line_item['summary'])
        self.assertEqual(form.get_request_metadata()['line_items'][0]['quantity'], '1')

    def test_payment_request_form_accepts_others_row_type(self):
        image_bytes = BytesIO()
        Image.new('RGB', (2, 2), 'white').save(image_bytes, format='JPEG')
        form = FundRequestForm(
            data={
                'requester_name': 'Requester Five',
                'request_date': '2026-05-04',
                'department': 'Operations',
                'branch': 'Alabang',
                'purpose_of_request': 'Other expense',
                'mode_of_release': 'cash',
                'supplier_details_known': 'no',
                'line_items_payload': json.dumps(
                    [
                        {
                            'row_type': 'others',
                            'category': 'Others',
                            'description': 'Miscellaneous fee',
                            'quantity': '1',
                            'unit_of_measurement': 'lot',
                            'estimated_cost': '750',
                        }
                    ]
                ),
            },
            files={
                'request_images': SimpleUploadedFile('proof.jpg', image_bytes.getvalue(), content_type='image/jpeg'),
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_line_items()[0]['row_type'], 'others')
        self.assertEqual(form.get_request_metadata()['line_items'][0]['row_type'], 'others')


class PaymentRequestTemplateSyncTests(TestCase):
    def test_pending_requests_sync_to_new_default_template_only(self):
        old_template = FundRequestTemplate.objects.create(
            name='Old Template',
            file=SimpleUploadedFile('old-template.docx', _build_docx_template_bytes('Old {{ ctrl_no }}')),
            is_active=True,
        )
        pending_request = FundRequest.objects.create(
            requester_name='Pending Requester',
            department='Operations',
            branch='Alabang',
            template=old_template,
            request_status='pending',
        )
        approved_request = FundRequest.objects.create(
            requester_name='Approved Requester',
            department='Operations',
            branch='Alabang',
            template=old_template,
            request_status='approved',
        )
        new_template = FundRequestTemplate.objects.create(
            name='New Template',
            file=SimpleUploadedFile('new-template.docx', _build_docx_template_bytes('New {{ ctrl_no }}')),
            is_active=True,
        )

        synced_count = views._sync_pending_fund_requests_to_template(new_template)

        pending_request.refresh_from_db()
        approved_request.refresh_from_db()
        self.assertEqual(synced_count, 1)
        self.assertEqual(pending_request.template_id, new_template.pk)
        self.assertEqual(approved_request.template_id, old_template.pk)


class FileManagerRoleRenameTests(TestCase):
    def setUp(self):
        self.system_owner = get_user_model().objects.create_user(username='system-owner', password='password')
        self.member = get_user_model().objects.create_user(username='artist-user', password='password')
        self.branch = ManagedFileNode.objects.create(
            owner=self.system_owner,
            name='Main Branch',
            node_type='folder',
            access_scope='shared',
            branch_name_snapshot='Main Branch',
        )
        self.department = ManagedFileNode.objects.create(
            parent=self.branch,
            owner=self.system_owner,
            name='Creative',
            node_type='folder',
            access_scope='shared',
            branch_name_snapshot='Main Branch',
            department_name_snapshot='Creative',
        )

    def _create_role_folder(self, name):
        return ManagedFileNode.objects.create(
            parent=self.department,
            owner=self.system_owner,
            name=name,
            node_type='folder',
            access_scope='shared',
            branch_name_snapshot='Main Branch',
            department_name_snapshot='Creative',
            role_name_snapshot=name,
        )

    def test_role_rename_updates_existing_file_manager_role_folder(self):
        old_role_folder = self._create_role_folder('Graphic Designer')
        user_folder = ManagedFileNode.objects.create(
            parent=old_role_folder,
            owner=self.member,
            name=self.member.username,
            node_type='folder',
            access_scope='private',
            branch_name_snapshot='Main Branch',
            department_name_snapshot='Creative',
            role_name_snapshot='Graphic Designer',
        )

        updated_count = views._sync_file_manager_role_rename('Graphic Designer', 'Graphic Artist', updated_by=self.system_owner)

        old_role_folder.refresh_from_db()
        user_folder.refresh_from_db()
        self.assertEqual(updated_count, 1)
        self.assertEqual(old_role_folder.name, 'Graphic Artist')
        self.assertEqual(old_role_folder.role_name_snapshot, 'Graphic Artist')
        self.assertTrue(old_role_folder.is_role_folder)
        self.assertEqual(user_folder.parent_id, old_role_folder.pk)
        self.assertEqual(user_folder.role_name_snapshot, 'Graphic Artist')

    def test_role_rename_merges_old_folder_when_new_folder_already_exists(self):
        old_role_folder = self._create_role_folder('Graphic Designer')
        new_role_folder = self._create_role_folder('Graphic Artist')
        user_folder = ManagedFileNode.objects.create(
            parent=old_role_folder,
            owner=self.member,
            name=self.member.username,
            node_type='folder',
            access_scope='private',
            branch_name_snapshot='Main Branch',
            department_name_snapshot='Creative',
            role_name_snapshot='Graphic Designer',
        )
        ManagedFilePermission.objects.create(node=old_role_folder, user=self.member, access_level='read')

        updated_count = views._sync_file_manager_role_rename('Graphic Designer', 'Graphic Artist', updated_by=self.system_owner)

        user_folder.refresh_from_db()
        new_role_folder.refresh_from_db()
        self.assertEqual(updated_count, 1)
        self.assertFalse(ManagedFileNode.objects.filter(pk=old_role_folder.pk).exists())
        self.assertEqual(user_folder.parent_id, new_role_folder.pk)
        self.assertEqual(user_folder.role_name_snapshot, 'Graphic Artist')
        self.assertTrue(new_role_folder.is_role_folder)
        self.assertTrue(ManagedFilePermission.objects.filter(node=new_role_folder, user=self.member, access_level='read').exists())

    def test_role_update_view_uses_role_name_before_form_mutation(self):
        role = Group.objects.create(name='Graphic Artist')
        role_folder = self._create_role_folder('Graphic Artist')
        self.system_owner.user_permissions.add(Permission.objects.get(codename='change_group'))
        self.client.force_login(self.system_owner)

        response = self.client.post(
            reverse('roles_update', args=[role.pk]),
            {
                'name': 'Creatives',
                'permissions': [],
            },
        )

        role.refresh_from_db()
        role_folder.refresh_from_db()
        self.assertRedirects(response, reverse('roles_list'), fetch_redirect_response=False)
        self.assertEqual(role.name, 'Creatives')
        self.assertEqual(role_folder.name, 'Creatives')
        self.assertEqual(role_folder.role_name_snapshot, 'Creatives')
        self.assertTrue(role_folder.is_role_folder)

    def test_default_hierarchy_marks_collapsed_department_role_folder(self):
        role = Group.objects.create(name='CSR')
        self.member.groups.add(role)
        self.member.profile.branch = 'Avantech'
        self.member.profile.save(update_fields=['branch'])

        views._ensure_file_manager_default_hierarchy()

        role_folder = ManagedFileNode.objects.get(name='CSR', parent__name='Avantech', access_scope='shared')
        self.assertTrue(role_folder.is_role_folder)
        self.assertEqual(role_folder.department_name_snapshot, 'CSR')
        self.assertEqual(role_folder.role_name_snapshot, 'CSR')


class FileManagerRenameTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='jaime0288', password='password')
        self.parent = ManagedFileNode.objects.create(
            owner=self.owner,
            name='Unassigned Branch',
            node_type='folder',
            access_scope='private',
        )
        self.client.force_login(self.owner)

    def test_owner_can_rename_file_without_global_change_permission(self):
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_rename'),
            {'node_id': str(file_node.pk), 'new_name': 'CD - Request for Funds Updated.docx'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        file_node.refresh_from_db()
        self.assertEqual(file_node.name, 'CD - Request for Funds Updated.docx')

    def test_file_rename_preserves_extension_when_new_name_has_no_extension(self):
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_rename'),
            {'node_id': str(file_node.pk), 'new_name': 'Payment Request'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        file_node.refresh_from_db()
        self.assertEqual(file_node.name, 'Payment Request.docx')

    def test_file_rename_preserves_original_extension_when_new_name_has_different_extension(self):
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_rename'),
            {'node_id': str(file_node.pk), 'new_name': 'Payment Request.pdf'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        file_node.refresh_from_db()
        self.assertEqual(file_node.name, 'Payment Request.docx')

    def test_rename_existing_name_prompts_for_keep_both(self):
        ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='Existing.docx',
            node_type='file',
            access_scope='private',
        )
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='Draft.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_rename'),
            {'node_id': str(file_node.pk), 'new_name': 'Existing.docx'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload['ok'])
        self.assertTrue(payload['conflict'])
        self.assertEqual(payload['available_name'], 'Existing (2).docx')
        file_node.refresh_from_db()
        self.assertEqual(file_node.name, 'Draft.docx')

    def test_rename_same_basename_different_extension_does_not_prompt(self):
        ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='Existing.pdf',
            node_type='file',
            access_scope='private',
        )
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='Draft.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_rename'),
            {'node_id': str(file_node.pk), 'new_name': 'Existing.docx'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        file_node.refresh_from_db()
        self.assertEqual(file_node.name, 'Existing.docx')

    def test_rename_existing_name_can_keep_both_with_copy_suffix(self):
        ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='Existing.docx',
            node_type='file',
            access_scope='private',
        )
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='Draft.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_rename'),
            {
                'node_id': str(file_node.pk),
                'new_name': 'Existing.docx',
                'conflict_resolution': 'keep_both',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        file_node.refresh_from_db()
        self.assertEqual(file_node.name, 'Existing (2).docx')

    def test_file_manager_page_does_not_javascript_escape_rename_prompt_name(self):
        self.owner.user_permissions.add(Permission.objects.get(codename='view_managedfilenode'))
        ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.get(reverse('file_manager_list'), {'node': self.parent.pk})

        self.assertContains(response, 'data-current-name="CD - Request for Funds.docx"')
        self.assertContains(response, 'data-node-id=')
        self.assertNotContains(response, 'class="fm-rename-form"')
        self.assertNotContains(response, r'CD \u002D Request for Funds.docx')


class FileManagerMoveTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='jaime0288', password='password')
        self.source = ManagedFileNode.objects.create(
            owner=self.owner,
            name='Source',
            node_type='folder',
            access_scope='private',
        )
        self.target = ManagedFileNode.objects.create(
            owner=self.owner,
            name='Target',
            node_type='folder',
            access_scope='private',
        )
        self.client.force_login(self.owner)

    def test_bulk_move_moves_multiple_files_and_folders(self):
        file_node = ManagedFileNode.objects.create(
            parent=self.source,
            owner=self.owner,
            name='notes.txt',
            node_type='file',
            access_scope='private',
        )
        folder_node = ManagedFileNode.objects.create(
            parent=self.source,
            owner=self.owner,
            name='Projects',
            node_type='folder',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_bulk_action'),
            {
                'selected_ids': f'{file_node.pk},{folder_node.pk}',
                'bulk_action': 'move',
                'target_parent_id': str(self.target.pk),
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('node_id'), self.target.pk)
        file_node.refresh_from_db()
        folder_node.refresh_from_db()
        self.assertEqual(file_node.parent_id, self.target.pk)
        self.assertEqual(folder_node.parent_id, self.target.pk)

    def test_bulk_move_skips_child_when_parent_is_also_selected(self):
        folder_node = ManagedFileNode.objects.create(
            parent=self.source,
            owner=self.owner,
            name='Projects',
            node_type='folder',
            access_scope='private',
        )
        child_file = ManagedFileNode.objects.create(
            parent=folder_node,
            owner=self.owner,
            name='plan.txt',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_bulk_action'),
            {
                'selected_ids': f'{folder_node.pk},{child_file.pk}',
                'bulk_action': 'move',
                'target_parent_id': str(self.target.pk),
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        folder_node.refresh_from_db()
        child_file.refresh_from_db()
        self.assertEqual(folder_node.parent_id, self.target.pk)
        self.assertEqual(child_file.parent_id, folder_node.pk)
        self.assertIn('1 item(s) skipped', response.json().get('message', ''))

    def test_bulk_move_uses_available_name_on_conflict(self):
        ManagedFileNode.objects.create(
            parent=self.target,
            owner=self.owner,
            name='notes.txt',
            node_type='file',
            access_scope='private',
        )
        file_node = ManagedFileNode.objects.create(
            parent=self.source,
            owner=self.owner,
            name='notes.txt',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_bulk_action'),
            {
                'selected_ids': str(file_node.pk),
                'bulk_action': 'move',
                'target_parent_id': str(self.target.pk),
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        file_node.refresh_from_db()
        self.assertEqual(file_node.parent_id, self.target.pk)
        self.assertEqual(file_node.name, 'notes (2).txt')


class FileManagerTrashTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='jaime0288', password='password')
        self.parent = ManagedFileNode.objects.create(
            owner=self.owner,
            name='Unassigned Branch',
            node_type='folder',
            access_scope='private',
        )
        self.client.force_login(self.owner)

    def test_delete_moves_owned_file_to_trash_without_global_delete_permission(self):
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_bulk_action'),
            {'selected_ids': str(file_node.pk), 'bulk_action': 'delete'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('node_id'), self.parent.pk)
        file_node.refresh_from_db()
        trash_node = ManagedFileNode.objects.get(parent__isnull=True, owner=self.owner, name='Trash')
        self.assertEqual(file_node.parent_id, trash_node.pk)
        self.assertEqual(file_node.name, 'CD - Request for Funds.docx')

    def test_file_manager_page_hides_trash_root_from_regular_user(self):
        self.owner.user_permissions.add(Permission.objects.get(codename='view_managedfilenode'))
        trash_node = views._get_or_create_file_manager_trash_folder(self.owner)

        response = self.client.get(reverse('file_manager_list'), {'node': self.parent.pk})

        self.assertNotContains(response, f'?node={trash_node.pk}')
        self.assertNotContains(response, '>Trash</span>')

    def test_file_manager_terminal_is_hidden_from_regular_user(self):
        self.owner.user_permissions.add(Permission.objects.get(codename='view_managedfilenode'))

        response = self.client.get(reverse('file_manager_list'), {'node': self.parent.pk})

        self.assertNotContains(response, 'id="fileManagerCliToggle"')
        self.assertNotContains(response, 'id="fileManagerCliPanel"')
        self.assertContains(response, 'const canUseFileManagerSudo = false;')

    def test_regular_user_cannot_run_sudo_file_manager_delete(self):
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_bulk_action'),
            {'selected_ids': str(file_node.pk), 'bulk_action': 'delete', 'sudo': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json().get('message'), 'Only superusers can run sudo commands.')
        file_node.refresh_from_db()
        self.assertEqual(file_node.parent_id, self.parent.pk)

    def test_regular_user_cannot_open_trash_root_directly(self):
        self.owner.user_permissions.add(Permission.objects.get(codename='view_managedfilenode'))
        trash_node = views._get_or_create_file_manager_trash_folder(self.owner)

        response = self.client.get(reverse('file_manager_list'), {'node': trash_node.pk})

        self.assertNotContains(response, '>Trash</span>')
        self.assertNotContains(response, 'Scope:</strong> Trash')

    def test_superuser_can_see_trash_root(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='password')
        trash_node = views._get_or_create_file_manager_trash_folder(self.owner)
        self.client.force_login(admin)

        response = self.client.get(reverse('file_manager_list'))

        self.assertContains(response, f'?node={trash_node.pk}')
        self.assertContains(response, 'Trash')

    def test_superuser_can_see_file_manager_terminal(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='password')
        self.client.force_login(admin)

        response = self.client.get(reverse('file_manager_list'))

        self.assertContains(response, 'id="fileManagerCliToggle"')
        self.assertContains(response, 'id="fileManagerCliPanel"')
        self.assertContains(response, 'const canUseFileManagerSudo = true;')

    def test_superuser_can_see_file_manager_page_access_indicator(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='password')
        self.client.force_login(admin)

        response = self.client.get(reverse('file_manager_list'))

        self.assertContains(response, 'View page access')
        self.assertContains(response, 'Who can access this page')
        self.assertContains(response, 'File Manager')
        self.assertContains(response, 'View managed file node')

    def test_duplicate_trash_roots_are_merged_into_one_system_trash(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='password')
        other_user = get_user_model().objects.create_user(username='other-user', password='password')
        first_trash = ManagedFileNode.objects.create(parent=None, owner=self.owner, name='Trash', node_type='folder', access_scope='private')
        second_trash = ManagedFileNode.objects.create(parent=None, owner=other_user, name='Trash', node_type='folder', access_scope='private')
        trashed_file = ManagedFileNode.objects.create(
            parent=second_trash,
            owner=other_user,
            name='Old File.docx',
            node_type='file',
            access_scope='private',
        )

        system_trash = views._get_or_create_file_manager_trash_folder(admin)

        trashed_file.refresh_from_db()
        self.assertEqual(system_trash.owner_id, admin.pk)
        self.assertEqual(ManagedFileNode.objects.filter(parent__isnull=True, name__iexact='Trash').count(), 1)
        self.assertFalse(ManagedFileNode.objects.filter(pk=first_trash.pk).exists())
        self.assertFalse(ManagedFileNode.objects.filter(pk=second_trash.pk).exists())
        self.assertEqual(trashed_file.parent_id, system_trash.pk)

    def test_delete_uses_available_name_when_trash_already_has_same_file_name(self):
        trash_node = views._get_or_create_file_manager_trash_folder(self.owner)
        ManagedFileNode.objects.create(
            parent=trash_node,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.post(
            reverse('file_manager_bulk_action'),
            {'selected_ids': str(file_node.pk), 'bulk_action': 'delete'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        file_node.refresh_from_db()
        self.assertEqual(file_node.parent_id, trash_node.pk)
        self.assertEqual(file_node.name, 'CD - Request for Funds (2).docx')

    def test_file_manager_page_has_delete_context_action_without_nested_delete_form(self):
        self.owner.user_permissions.add(Permission.objects.get(codename='view_managedfilenode'))
        file_node = ManagedFileNode.objects.create(
            parent=self.parent,
            owner=self.owner,
            name='CD - Request for Funds.docx',
            node_type='file',
            access_scope='private',
        )

        response = self.client.get(reverse('file_manager_list'), {'node': self.parent.pk})

        self.assertContains(response, f'data-node-id="{file_node.pk}"')
        self.assertContains(response, 'fm-delete-btn')
        self.assertContains(response, '>Delete</button>')
        self.assertNotContains(response, 'class="fm-rename-form"')


class ImageUploadConversionTests(TestCase):
    def test_heic_upload_is_converted_to_jpeg(self):
        source = BytesIO()
        Image.new('RGB', (10, 10), 'red').save(source, format='HEIF')
        upload = SimpleUploadedFile('proof.heic', source.getvalue(), content_type='image/heic')

        converted = prepare_image_upload(upload, max_size_bytes=10 * 1024 * 1024, label='test image')

        self.assertEqual(converted.name, 'proof.jpg')
        with Image.open(converted) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertEqual(image.mode, 'RGB')


class AssetAccountabilityControlNumberTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='borrower', password='password')
        self.reviewer = get_user_model().objects.create_user(username='reviewer', password='password')
        self.department = AssetDepartment.objects.create(name='QA Control IT')
        self.item = AssetItem.objects.create(
            department=self.department,
            item_name='Laptop',
            item_type='laptop',
            stock_quantity=3,
            low_stock_threshold=1,
        )

    def test_pending_request_keeps_no_control_number_after_approval(self):
        accountability = AssetAccountability.objects.create(
            item=self.item,
            borrowed_by=self.user,
            quantity_borrowed=1,
            request_status='pending',
        )

        self.assertIsNone(accountability.control_number)
        self.assertIsNone(accountability.request_year)
        self.assertIsNone(accountability.control_sequence)

        self.assertTrue(accountability.mark_approved(processed_by=self.reviewer))
        accountability.refresh_from_db()

        self.assertIsNone(accountability.control_number)
        self.assertIsNone(accountability.request_year)
        self.assertIsNone(accountability.control_sequence)


class AssetAccountabilityPdfPayloadTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp(prefix='accountability-test-media-')
        self.user = get_user_model().objects.create_user(username='borrower', password='password')
        self.department = AssetDepartment.objects.create(name='QA PDF IT')
        self.item = AssetItem.objects.create(
            department=self.department,
            item_name='Laptop',
            item_type='laptop',
            specification='16GB RAM',
            stock_quantity=3,
            low_stock_threshold=1,
        )

    def tearDown(self):
        shutil.rmtree(self._media_root, ignore_errors=True)

    def test_accountability_template_download_payload_is_converted_pdf(self):
        with self.settings(MEDIA_ROOT=self._media_root):
            accountability = AssetAccountability.objects.create(
                item=self.item,
                borrowed_by=self.user,
                quantity_borrowed=1,
                request_status='approved',
            )
            form_batch = AssetAccountabilityFormBatch.objects.create(created_by=self.user)
            accountability.accountability_form_batch = form_batch
            accountability.save(update_fields=['accountability_form_batch', 'updated_at'])
            template = AssetAccountabilityTemplate.objects.create(
                name='Accountability Form',
                file=SimpleUploadedFile(
                    'accountability-template.docx',
                    _build_docx_template_bytes('Control: {{ control_number }}'),
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                ),
                is_active=True,
            )

            with patch.object(views, '_convert_office_bytes_to_pdf', return_value=b'%PDF-accountability') as converter:
                payload = views._build_accountability_template_file_payload(accountability)

            self.assertEqual(payload['content'], b'%PDF-accountability')
            self.assertEqual(payload['content_type'], 'application/pdf')
            self.assertEqual(payload['filename'], f'asset-accountability-{form_batch.control_number}.pdf')
            converter.assert_called_once()
            converted_source_bytes = converter.call_args.args[0]
            with zipfile.ZipFile(BytesIO(converted_source_bytes), 'r') as archive:
                document_xml = archive.read('word/document.xml').decode('utf-8')
            self.assertIn(form_batch.control_number, document_xml)
            template.file.delete(save=False)

    def test_accountability_template_uses_assigned_control_number_from_latest_record(self):
        with self.settings(MEDIA_ROOT=self._media_root):
            accountability = AssetAccountability.objects.create(
                item=self.item,
                borrowed_by=self.user,
                quantity_borrowed=1,
                request_status='pending',
            )
            stale_instance = accountability
            fresh_instance = AssetAccountability.objects.get(pk=accountability.pk)
            reviewer = get_user_model().objects.create_user(username='approver', password='password')
            self.assertTrue(fresh_instance.mark_approved(processed_by=reviewer))
            fresh_instance.refresh_from_db()
            form_batch = AssetAccountabilityFormBatch.objects.create(created_by=self.user)
            fresh_instance.accountability_form_batch = form_batch
            fresh_instance.save(update_fields=['accountability_form_batch', 'updated_at'])
            self.assertIsNone(stale_instance.control_number)

            template = AssetAccountabilityTemplate.objects.create(
                name='Accountability Form',
                file=SimpleUploadedFile(
                    'accountability-template.docx',
                    _build_docx_template_bytes('Control: {{ control_number }}'),
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                ),
                is_active=True,
            )

            with patch.object(views, '_convert_office_bytes_to_pdf', return_value=b'%PDF-accountability') as converter:
                payload = views._build_accountability_template_file_payload(stale_instance)

            self.assertEqual(payload['filename'], f'asset-accountability-{form_batch.control_number}.pdf')
            converted_source_bytes = converter.call_args.args[0]
            with zipfile.ZipFile(BytesIO(converted_source_bytes), 'r') as archive:
                document_xml = archive.read('word/document.xml').decode('utf-8')
            self.assertIn(form_batch.control_number, document_xml)
            template.file.delete(save=False)


class SupportTicketListLifecycleTests(TestCase):
    def setUp(self):
        self.reporter = get_user_model().objects.create_user(username='reporter', password='password')
        self.support_user = get_user_model().objects.create_superuser(
            username='support-admin',
            email='support@example.com',
            password='password',
        )

    def test_resolved_ticket_moves_out_of_active_list_and_into_past_tickets(self):
        active_ticket = SupportTicket.objects.create(
            title='Laptop cannot connect',
            description='Needs help',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='open',
        )
        resolved_ticket = SupportTicket.objects.create(
            title='Printer fixed',
            description='Already handled',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='resolved',
        )

        self.client.force_login(self.support_user)
        response = self.client.get(reverse('support_tickets_list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(active_ticket, response.context['ticket_page'].object_list)
        self.assertNotIn(resolved_ticket, response.context['ticket_page'].object_list)
        self.assertIn(resolved_ticket, list(response.context['past_tickets_preview']))
        self.assertEqual(response.context['resolved_count'], 1)

    def test_resolved_ticket_rejects_new_messages(self):
        resolved_ticket = SupportTicket.objects.create(
            title='Network restored',
            description='Already resolved',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='resolved',
        )

        self.client.force_login(self.reporter)
        response = self.client.post(
            reverse('support_ticket_add_message', args=[resolved_ticket.id]),
            {'message': 'Following up'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(resolved_ticket.messages.exists())

    def test_past_ticket_filters_apply_to_past_preview_only(self):
        active_ticket = SupportTicket.objects.create(
            title='Active keyboard problem',
            description='Still active',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='open',
        )
        matching_ticket = SupportTicket.objects.create(
            title='Printer fixed',
            description='Resolved printer issue',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='resolved',
            support_priority='high',
        )
        other_past_ticket = SupportTicket.objects.create(
            title='Monitor replaced',
            description='Closed monitor issue',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='closed',
            support_priority='low',
        )

        self.client.force_login(self.support_user)
        response = self.client.get(
            reverse('support_tickets_list'),
            {'past_q': 'printer', 'past_status': 'resolved', 'past_priority': 'high'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(active_ticket, response.context['ticket_page'].object_list)
        self.assertIn(matching_ticket, list(response.context['past_tickets_preview']))
        self.assertNotIn(other_past_ticket, list(response.context['past_tickets_preview']))
        self.assertTrue(response.context['should_open_past_modal'])

    def test_archived_ticket_filters_apply_to_archived_preview(self):
        matching_ticket = SupportTicket.objects.create(
            title='Archived network issue',
            description='Old network case',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='closed',
            support_priority='critical',
            is_archived=True,
            archived_by=self.support_user,
        )
        other_archived_ticket = SupportTicket.objects.create(
            title='Archived mouse issue',
            description='Old hardware case',
            created_by=self.reporter,
            assigned_to=self.support_user,
            status='resolved',
            support_priority='low',
            is_archived=True,
            archived_by=self.support_user,
        )

        self.client.force_login(self.support_user)
        response = self.client.get(
            reverse('support_tickets_list'),
            {'archived_q': 'network', 'archived_status': 'closed', 'archived_priority': 'critical'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(matching_ticket, list(response.context['archived_tickets_preview']))
        self.assertNotIn(other_archived_ticket, list(response.context['archived_tickets_preview']))
        self.assertTrue(response.context['should_open_archived_modal'])


class AccountabilityFormBatchHolderNameTests(TestCase):
    def setUp(self):
        self.department, _ = AssetDepartment.objects.get_or_create(name='IT')
        self.regular_user = get_user_model().objects.create_user(
            username='regular-user',
            first_name='Regular',
            last_name='User',
            password='password',
        )
        self.manager_user = get_user_model().objects.create_user(
            username='manager-user',
            first_name='Manager',
            last_name='User',
            password='password',
        )
        self.item = AssetItem.objects.create(
            department=self.department,
            item_name='Laptop',
            item_type='laptop',
            stock_quantity=5,
            created_by=self.regular_user,
        )

        add_permission = Permission.objects.get(codename='add_assetaccountability')
        manage_permission = Permission.objects.get(codename='can_manage_accountability')
        self.regular_user.user_permissions.add(add_permission)
        self.manager_user.user_permissions.add(add_permission, manage_permission)
        self.regular_record = AssetAccountability.objects.create(
            item=self.item,
            borrowed_by=self.regular_user,
            quantity_borrowed=1,
            request_status='approved',
            status='borrowed',
        )
        self.manager_record = AssetAccountability.objects.create(
            item=self.item,
            borrowed_by=self.manager_user,
            quantity_borrowed=1,
            request_status='approved',
            status='borrowed',
        )

    def _batch_payload(self, holder_name, record_id):
        return {
            'accountable_name': holder_name,
            'record_ids': [str(record_id)],
            'department': '',
            'position_role': '',
            'contact_number': '',
        }

    def test_regular_user_batch_form_renders_holder_name_as_readonly(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('accountability_form_batch_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="accountable_name"')
        self.assertContains(response, 'datalist id="holderNameOptions"')
        self.assertContains(response, 'readonly')
        self.assertContains(response, 'value="Regular User"')

    def test_regular_user_cannot_submit_custom_holder_name_in_batch_form(self):
        self.client.force_login(self.regular_user)
        response = self.client.post(
            reverse('accountability_form_batch_create'),
            self._batch_payload('Fake Holder', self.regular_record.pk),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You are not allowed to set a custom holder name.')
        self.regular_record.refresh_from_db()
        self.assertIsNone(self.regular_record.accountability_form_batch_id)

    def test_regular_user_submits_default_holder_name_in_batch_form(self):
        self.client.force_login(self.regular_user)
        response = self.client.post(
            reverse('accountability_form_batch_create'),
            self._batch_payload('Regular User', self.regular_record.pk),
        )

        self.assertEqual(response.status_code, 302)
        self.regular_record.refresh_from_db()
        self.assertEqual(self.regular_record.accountable_name, 'Regular User')
        self.assertIsNotNone(self.regular_record.accountability_form_batch_id)

    def test_manager_user_can_submit_custom_holder_name_in_batch_form(self):
        self.client.force_login(self.manager_user)
        response = self.client.post(
            reverse('accountability_form_batch_create'),
            self._batch_payload('Custom Holder Name', self.manager_record.pk),
        )

        self.assertEqual(response.status_code, 302)
        self.manager_record.refresh_from_db()
        self.assertEqual(self.manager_record.accountable_name, 'Custom Holder Name')


class FileManagerUploadTests(TestCase):
    def setUp(self):
        self._media_root = tempfile.mkdtemp(prefix='file-manager-test-media-')
        self.owner = get_user_model().objects.create_superuser(
            username='file-owner',
            email='owner@example.com',
            password='password',
        )
        self.user = get_user_model().objects.create_user(username='file-user', password='password')
        self.folder = ManagedFileNode.objects.create(
            name='file-user',
            node_type='folder',
            owner=self.owner,
            created_by=self.owner,
            updated_by=self.owner,
        )
        ManagedFilePermission.objects.create(
            node=self.folder,
            user=self.user,
            access_level='read_write',
            created_by=self.owner,
        )

    def tearDown(self):
        shutil.rmtree(self._media_root, ignore_errors=True)

    def test_user_with_folder_write_permission_can_upload_without_global_add_permission(self):
        self.client.force_login(self.user)
        with self.settings(MEDIA_ROOT=self._media_root):
            response = self.client.post(
                reverse('file_manager_upload'),
                {
                    'parent_id': str(self.folder.id),
                    'files': SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain'),
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        uploaded_node = ManagedFileNode.objects.get(parent=self.folder, name='notes.txt')
        self.assertEqual(uploaded_node.owner, self.user)

    def test_user_with_read_only_folder_permission_cannot_upload(self):
        ManagedFilePermission.objects.filter(node=self.folder, user=self.user).update(access_level='read')
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('file_manager_upload'),
            {
                'parent_id': str(self.folder.id),
                'files': SimpleUploadedFile('blocked.txt', b'hello', content_type='text/plain'),
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['ok'])
        self.assertFalse(ManagedFileNode.objects.filter(parent=self.folder, name='blocked.txt').exists())

    def test_duplicate_upload_name_prompts_for_keep_both(self):
        ManagedFileNode.objects.create(
            parent=self.folder,
            name='notes.txt',
            node_type='file',
            owner=self.user,
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.force_login(self.user)

        with self.settings(MEDIA_ROOT=self._media_root):
            response = self.client.post(
                reverse('file_manager_upload'),
                {
                    'parent_id': str(self.folder.id),
                    'files': SimpleUploadedFile('notes.txt', b'new copy', content_type='text/plain'),
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload['ok'])
        self.assertTrue(payload['conflict'])
        self.assertEqual(payload['available_name'], 'notes (2).txt')
        self.assertFalse(ManagedFileNode.objects.filter(parent=self.folder, name='notes (2).txt').exists())

    def test_upload_same_basename_different_extension_does_not_prompt(self):
        ManagedFileNode.objects.create(
            parent=self.folder,
            name='notes.pdf',
            node_type='file',
            owner=self.user,
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.force_login(self.user)

        with self.settings(MEDIA_ROOT=self._media_root):
            response = self.client.post(
                reverse('file_manager_upload'),
                {
                    'parent_id': str(self.folder.id),
                    'files': SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain'),
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertTrue(ManagedFileNode.objects.filter(parent=self.folder, name='notes.txt').exists())

    def test_duplicate_upload_name_can_keep_both_with_copy_suffix(self):
        ManagedFileNode.objects.create(
            parent=self.folder,
            name='notes.txt',
            node_type='file',
            owner=self.user,
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.force_login(self.user)

        with self.settings(MEDIA_ROOT=self._media_root):
            response = self.client.post(
                reverse('file_manager_upload'),
                {
                    'parent_id': str(self.folder.id),
                    'files': SimpleUploadedFile('notes.txt', b'new copy', content_type='text/plain'),
                    'conflict_resolution': 'keep_both',
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertTrue(ManagedFileNode.objects.filter(parent=self.folder, name='notes (2).txt').exists())

    def test_duplicate_folder_level_is_collapsed(self):
        branch = ManagedFileNode.objects.create(
            name='Avantech',
            node_type='folder',
            owner=self.owner,
            created_by=self.owner,
            updated_by=self.owner,
        )
        csr = ManagedFileNode.objects.create(
            parent=branch,
            name='CSR',
            node_type='folder',
            owner=self.owner,
            created_by=self.owner,
            updated_by=self.owner,
        )
        duplicate_csr = ManagedFileNode.objects.create(
            parent=csr,
            name='CSR',
            node_type='folder',
            owner=self.owner,
            created_by=self.owner,
            updated_by=self.owner,
        )
        user_folder = ManagedFileNode.objects.create(
            parent=duplicate_csr,
            name='agent-user',
            node_type='folder',
            owner=self.user,
            created_by=self.owner,
            updated_by=self.owner,
        )

        views._collapse_duplicate_file_manager_folder_levels()

        user_folder.refresh_from_db()
        self.assertEqual(user_folder.parent, csr)
        self.assertFalse(ManagedFileNode.objects.filter(pk=duplicate_csr.pk).exists())

    def test_super_user_without_branch_uses_existing_super_user_branch(self):
        super_group = Group.objects.create(name='Super Users')
        first_super = get_user_model().objects.create_superuser(
            username='first-super',
            email='first@example.com',
            password='password',
        )
        second_super = get_user_model().objects.create_superuser(
            username='second-super',
            email='second@example.com',
            password='password',
        )
        first_super.groups.add(super_group)
        second_super.groups.add(super_group)
        first_super.profile.branch = 'Alabang'
        first_super.profile.save(update_fields=['branch'])

        views._ensure_file_manager_default_hierarchy()

        super_users_node = ManagedFileNode.objects.get(parent__name='Alabang', name='Super Users')
        self.assertEqual(
            set(super_users_node.children.values_list('name', flat=True)),
            {'first-super', 'second-super'},
        )
        self.assertFalse(ManagedFileNode.objects.filter(parent__name='Unassigned Branch', name='Super Users').exists())
