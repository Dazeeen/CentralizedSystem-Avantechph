from django.db import migrations, models


def backfill_liquidation_control_numbers(apps, schema_editor):
    Liquidation = apps.get_model('core', 'Liquidation')
    queryset = Liquidation.objects.all().order_by('created_at', 'id')
    year_counters = {}
    for liquidation in queryset:
        liquidation_date = liquidation.liquidation_date
        year = int(getattr(liquidation_date, 'year', 0) or 0)
        if not year:
            continue
        next_sequence = year_counters.get(year, 0) + 1
        year_counters[year] = next_sequence
        liquidation.request_year = year
        liquidation.control_sequence = next_sequence
        liquidation.control_number = f'{year}-{next_sequence:04d}'
        liquidation.save(update_fields=['request_year', 'control_sequence', 'control_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_liquidation_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='liquidation',
            name='control_number',
            field=models.CharField(blank=True, editable=False, max_length=9, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='liquidation',
            name='control_sequence',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='liquidation',
            name='request_year',
            field=models.PositiveIntegerField(blank=True, db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(backfill_liquidation_control_numbers, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='liquidation',
            constraint=models.UniqueConstraint(fields=('request_year', 'control_sequence'), name='unique_liquidation_year_sequence'),
        ),
    ]
