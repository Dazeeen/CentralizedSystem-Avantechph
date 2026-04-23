from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_clientquotation_product_package'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientquotation',
            name='scanned_document',
            field=models.FileField(blank=True, null=True, upload_to='client_quotations/'),
        ),
    ]
