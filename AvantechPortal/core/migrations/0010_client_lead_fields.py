from django.db import migrations, models

import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_clientquotation_scanned_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='lead_disposition_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='client',
            name='lead_proof_image',
            field=models.FileField(blank=True, null=True, upload_to=core.models.client_lead_proof_upload_to),
        ),
        migrations.AddField(
            model_name='client',
            name='lead_status',
            field=models.CharField(choices=[('intake', 'Intake'), ('converted', 'Converted'), ('lost', 'Lost'), ('qualified', 'Qualified'), ('not_qualified', 'Not Qualified')], default='intake', max_length=20),
        ),
    ]
