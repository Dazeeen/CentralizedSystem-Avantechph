import shutil
import tempfile
import zipfile
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from . import views
from .models import AssetAccountability, AssetAccountabilityFormBatch, AssetAccountabilityTemplate, AssetDepartment, AssetItem


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
