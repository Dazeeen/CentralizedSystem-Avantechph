from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_clientquotation'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientquotation',
            name='product_package',
            field=models.CharField(default='', max_length=150),
        ),
    ]
