from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def mark_existing_liquidations_approved(apps, schema_editor):
    Liquidation = apps.get_model('core', 'Liquidation')
    for liquidation in Liquidation.objects.all().iterator():
        liquidation.request_status = 'approved'
        if not liquidation.processed_at:
            liquidation.processed_at = liquidation.created_at
        liquidation.save(update_fields=['request_status', 'processed_at', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_liquidationsettings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='liquidation',
            name='decision_reason',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='liquidation',
            name='processed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='liquidation',
            name='processed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidations_processed', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='liquidation',
            name='request_status',
            field=models.CharField(choices=[('pending', 'For Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=20),
        ),
        migrations.RunPython(mark_existing_liquidations_approved, migrations.RunPython.noop),
    ]
