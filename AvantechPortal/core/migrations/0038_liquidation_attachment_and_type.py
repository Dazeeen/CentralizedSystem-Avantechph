from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_liquidation_control_number_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='liquidation',
            name='returned_or_over_type',
            field=models.CharField(choices=[('returned', 'Returned'), ('over', 'Over')], default='returned', max_length=20),
        ),
        migrations.CreateModel(
            name='LiquidationAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to=core.models.liquidation_attachment_upload_to)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('liquidation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='core.liquidation')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidation_attachments_uploaded', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
