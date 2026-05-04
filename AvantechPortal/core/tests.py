import shutil
import tempfile
import zipfile
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from . import views
from .forms import AssetItemForm, RoleForm, prepare_image_upload
from .permission_catalog import BASIC_ROLE_PERMISSION_KEYS, get_basic_role_permission_ids
from .models import (
    AssetAccountability,
    AssetAccountabilityFormBatch,
    AssetAccountabilityTemplate,
    AssetDepartment,
    AssetItem,
    AssetItemType,
    ManagedFileNode,
    ManagedFilePermission,
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

    def test_duplicate_upload_name_gets_copy_suffix(self):
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
