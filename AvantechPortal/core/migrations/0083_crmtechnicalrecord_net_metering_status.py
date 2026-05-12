from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0082_crmclient_section_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='net_metering_status',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
