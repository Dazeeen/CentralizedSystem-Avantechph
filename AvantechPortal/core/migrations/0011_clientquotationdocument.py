from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_client_lead_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientQuotationDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=core.models.client_quotation_upload_to)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('quotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='core.clientquotation')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_quotation_documents_uploaded', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
