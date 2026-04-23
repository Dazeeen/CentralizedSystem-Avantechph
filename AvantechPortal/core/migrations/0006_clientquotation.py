from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_client'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientQuotation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.PositiveIntegerField()),
                ('quoted_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('quotation_notes', models.TextField(blank=True)),
                ('negotiation_status', models.CharField(choices=[('sent', 'Sent'), ('under_negotiation', 'Under Negotiation'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='sent', max_length=20)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quotations', to='core.client')),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_quotations_sent', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='clientquotation',
            constraint=models.UniqueConstraint(fields=('client', 'version'), name='unique_client_quotation_version'),
        ),
    ]
