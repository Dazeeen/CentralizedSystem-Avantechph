from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_liquidation_attachment_and_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='LiquidationSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_selectable_rows', models.PositiveIntegerField(default=20)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Liquidation Settings',
                'verbose_name_plural': 'Liquidation Settings',
            },
        ),
    ]
