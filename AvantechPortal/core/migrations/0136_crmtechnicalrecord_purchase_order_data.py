from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0135_crmtechnicalrecord_order_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='purchase_order_data',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
