from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_existing_pipelines(apps, schema_editor):
    SalesRecord = apps.get_model('core', 'CRMSalesRecord')
    Pipeline = apps.get_model('core', 'ERPProjectPipeline')
    stage_map = {
        'new': 'lead',
        'contacted': 'qualification',
        'contracted': 'qualification',
        'for survey': 'survey',
        'for proposal': 'quotation',
        'forproposal': 'quotation',
        'negotiation': 'negotiation',
        'closed lost': 'closed_lost',
        'close lost': 'closed_lost',
        'closed won': 'accounting',
        'close won': 'accounting',
    }
    pipelines = []
    for sales_record in SalesRecord.objects.all().iterator():
        status = (sales_record.sales_status or '').strip().lower()
        stage = stage_map.get(status, 'lead')
        if status in {'closed won', 'close won'} and not (sales_record.job_order_number or '').strip():
            stage = 'sales_order'
        pipelines.append(Pipeline(sales_record_id=sales_record.pk, stage=stage))
    Pipeline.objects.bulk_create(pipelines, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0126_alter_activitylog_category'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ERPProjectPipeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stage', models.CharField(choices=[('lead', 'Lead / New Client'), ('qualification', 'Qualification / Needs Analysis'), ('survey', 'Site Survey'), ('quotation', 'Quotation / Proposal'), ('negotiation', 'Negotiation'), ('sales_order', 'Closed Won / Job Order'), ('accounting', 'Accounting Clearance'), ('materials', 'Material Readiness / Procurement'), ('technical_planning', 'Technical Planning'), ('scheduled', 'Installation Scheduled'), ('installation', 'Installation in Progress'), ('quality', 'Quality Assurance'), ('handover', 'Billing and Client Turnover'), ('aftersales', 'Aftersales / Warranty'), ('closed_lost', 'Closed Lost')], db_index=True, default='lead', max_length=30)),
                ('accounting_status', models.CharField(choices=[('pending', 'Pending Review'), ('cleared', 'Cleared'), ('on_hold', 'On Hold')], db_index=True, default='pending', max_length=20)),
                ('procurement_status', models.CharField(choices=[('not_assessed', 'Not Assessed'), ('not_required', 'Not Required'), ('requested', 'Material Request Raised'), ('ordered', 'Purchase Order Issued'), ('received', 'Materials Received')], db_index=True, default='not_assessed', max_length=20)),
                ('material_status', models.CharField(choices=[('pending', 'Pending Check'), ('reserved', 'Reserved'), ('released', 'Released to Project'), ('not_required', 'Not Required')], db_index=True, default='pending', max_length=20)),
                ('quality_status', models.CharField(choices=[('pending', 'Pending Inspection'), ('passed', 'QC Passed'), ('failed', 'QC Failed / Rework')], db_index=True, default='pending', max_length=20)),
                ('handover_status', models.CharField(choices=[('pending', 'Pending Turnover'), ('completed', 'Turnover Completed')], db_index=True, default='pending', max_length=20)),
                ('accounting_notes', models.TextField(blank=True)),
                ('operations_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_transition_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='erp_pipeline_transitions', to=settings.AUTH_USER_MODEL)),
                ('sales_record', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='erp_pipeline', to='core.crmsalesrecord')),
            ],
            options={
                'ordering': ['-updated_at', '-id'],
                'permissions': [('manage_erp_accounting_gate', 'Can clear ERP projects for accounting'), ('manage_erp_material_gate', 'Can manage ERP procurement and material readiness'), ('manage_erp_quality_gate', 'Can manage ERP quality and turnover gates')],
            },
        ),
        migrations.CreateModel(
            name='ERPWorkflowEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_stage', models.CharField(blank=True, max_length=30)),
                ('to_stage', models.CharField(max_length=30)),
                ('action', models.CharField(max_length=80)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='erp_workflow_events', to=settings.AUTH_USER_MODEL)),
                ('pipeline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='core.erpprojectpipeline')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.RunPython(create_existing_pipelines, migrations.RunPython.noop),
    ]
