from django.db import migrations, models
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0128_erpprojectpipeline_procurement_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ERPWorkflowSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('next_purchase_order_year', models.PositiveIntegerField(default=core.models.current_year)),
                ('next_purchase_order_sequence', models.PositiveIntegerField(default=1)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'ERP Workflow Setting',
                'verbose_name_plural': 'ERP Workflow Settings',
            },
        ),
    ]
