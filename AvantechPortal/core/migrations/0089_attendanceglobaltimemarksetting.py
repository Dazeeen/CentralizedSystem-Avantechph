from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_existing_user_settings_to_global(apps, schema_editor):
    UserSetting = apps.get_model('core', 'AttendanceTimemarkSetting')
    GlobalSetting = apps.get_model('core', 'AttendanceGlobalTimemarkSetting')

    existing = UserSetting.objects.order_by('-updated_at').first()
    if not existing:
        GlobalSetting.objects.get_or_create(key='global')
        return

    global_setting, _ = GlobalSetting.objects.get_or_create(
        key='global',
        defaults={
            'company_name': existing.company_name or '',
            'location': existing.location or '',
            'logo_data': existing.logo_data or '',
            'layout': existing.layout or {},
            'updated_by_id': existing.user_id,
        },
    )

    if _:
        return

    global_setting.company_name = existing.company_name or ''
    global_setting.location = existing.location or ''
    global_setting.logo_data = existing.logo_data or ''
    global_setting.layout = existing.layout or {}
    global_setting.updated_by_id = existing.user_id
    global_setting.save(update_fields=['company_name', 'location', 'logo_data', 'layout', 'updated_by', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0088_attendancetimemarksetting'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceGlobalTimemarkSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(default='global', max_length=32, unique=True)),
                ('company_name', models.CharField(blank=True, default='', max_length=255)),
                ('location', models.CharField(blank=True, default='', max_length=255)),
                ('logo_data', models.TextField(blank=True, default='')),
                ('layout', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_global_timemark_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.RunPython(migrate_existing_user_settings_to_global, migrations.RunPython.noop),
    ]
