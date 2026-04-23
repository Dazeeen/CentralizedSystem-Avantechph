from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_assetitemtype_assetitemimage_and_itemtype_refactor'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='branch',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
    ]
