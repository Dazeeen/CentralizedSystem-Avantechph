from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_assetaccountability_request_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='assetitem',
            name='asset_image',
            field=models.ImageField(blank=True, null=True, upload_to='asset_images/'),
        ),
    ]
