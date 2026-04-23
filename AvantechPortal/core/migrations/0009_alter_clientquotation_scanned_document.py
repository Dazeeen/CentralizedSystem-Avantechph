from django.db import migrations, models

import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_clientquotation_scanned_document'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientquotation',
            name='scanned_document',
            field=models.FileField(blank=True, null=True, upload_to=core.models.client_quotation_upload_to),
        ),
    ]
