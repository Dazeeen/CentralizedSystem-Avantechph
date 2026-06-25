from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_existing_purchase_orders(apps, schema_editor):
    Pipeline = apps.get_model('core', 'ERPProjectPipeline')
    TechnicalRecord = apps.get_model('core', 'CRMTechnicalRecord')
    purchase_orders = {
        row.sales_record_id: row.po_number
        for row in TechnicalRecord.objects.exclude(po_number='').iterator()
    }
    for pipeline in Pipeline.objects.filter(sales_record_id__in=purchase_orders).iterator():
        pipeline.purchase_order_number = purchase_orders[pipeline.sales_record_id]
        pipeline.save(update_fields=['purchase_order_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0127_erpprojectpipeline_erpworkflowevent'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='erpprojectpipeline',
            name='purchase_order_number',
            field=models.CharField(blank=True, db_index=True, max_length=80),
        ),
        migrations.AddField(
            model_name='erpprojectpipeline',
            name='procurement_responsible',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='erp_procurement_projects', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(copy_existing_purchase_orders, migrations.RunPython.noop),
    ]
