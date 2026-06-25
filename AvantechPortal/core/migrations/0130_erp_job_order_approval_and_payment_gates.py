from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def grandfather_existing_projects(apps, schema_editor):
    Pipeline = apps.get_model('core', 'ERPProjectPipeline')
    won_projects = Pipeline.objects.filter(
        sales_record__sales_status__in=['closed won', 'close won'],
    )
    won_projects.update(project_approval_status='approved')
    won_projects.filter(
        stage__in=['materials', 'technical_planning', 'scheduled', 'installation', 'quality', 'handover', 'aftersales'],
    ).update(supplier_quotation_status='not_required')
    won_projects.filter(stage__in=['handover', 'aftersales']).update(
        receiving_status='confirmed',
        invoice_status='verified',
        payment_status='paid',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0129_erpworkflowsetting'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='erpprojectpipeline',
            name='stage',
            field=models.CharField(choices=[('lead', 'Lead / New Client'), ('qualification', 'Qualification / Needs Analysis'), ('survey', 'Site Survey'), ('quotation', 'Quotation / Proposal'), ('negotiation', 'Negotiation'), ('sales_order', 'Closed Won / Job Order'), ('project_approval', 'Technical / Project Head Approval'), ('accounting', 'Accounting Clearance'), ('supplier_quotation', 'Supplier Quotation / Canvassing'), ('materials', 'Material Readiness / Procurement'), ('technical_planning', 'Technical Planning'), ('scheduled', 'Installation Scheduled'), ('installation', 'Installation in Progress'), ('quality', 'Quality Assurance'), ('receiving', 'Receiving / Completion Confirmation'), ('invoice_payment', 'Invoice and Payment Processing'), ('handover', 'Billing and Client Turnover'), ('aftersales', 'Aftersales / Warranty'), ('closed_lost', 'Closed Lost')], db_index=True, default='lead', max_length=30),
        ),
        migrations.AddField(model_name='erpprojectpipeline', name='project_approval_status', field=models.CharField(choices=[('pending', 'Pending Project Head Approval'), ('approved', 'Approved'), ('rejected', 'Rejected / For Revision')], db_index=True, default='pending', max_length=20)),
        migrations.AddField(model_name='erpprojectpipeline', name='project_approved_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='erpprojectpipeline', name='project_approved_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='erp_projects_approved', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='erpprojectpipeline', name='supplier_quotation_status', field=models.CharField(choices=[('pending', 'Pending Canvassing'), ('canvassing', 'Canvassing in Progress'), ('selected', 'Supplier Selected'), ('not_required', 'Not Required')], db_index=True, default='pending', max_length=20)),
        migrations.AddField(model_name='erpprojectpipeline', name='supplier_quotation_reference', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='erpprojectpipeline', name='receiving_status', field=models.CharField(choices=[('pending', 'Pending Confirmation'), ('confirmed', 'Received / Completed'), ('rejected', 'Rejected / Incomplete')], db_index=True, default='pending', max_length=20)),
        migrations.AddField(model_name='erpprojectpipeline', name='receiving_reference', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='erpprojectpipeline', name='invoice_status', field=models.CharField(choices=[('pending', 'Pending Invoice'), ('received', 'Invoice Received'), ('verified', 'Invoice Verified'), ('not_required', 'Not Required')], db_index=True, default='pending', max_length=20)),
        migrations.AddField(model_name='erpprojectpipeline', name='invoice_reference', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='erpprojectpipeline', name='payment_status', field=models.CharField(choices=[('pending', 'Pending Payment'), ('partial', 'Partially Paid'), ('paid', 'Paid'), ('not_required', 'Not Required')], db_index=True, default='pending', max_length=20)),
        migrations.AddField(model_name='erpprojectpipeline', name='payment_reference', field=models.CharField(blank=True, max_length=120)),
        migrations.RunPython(grandfather_existing_projects, migrations.RunPython.noop),
    ]
