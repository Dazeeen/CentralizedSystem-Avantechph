from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0087_attendancelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceTimemarkSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(blank=True, default='', max_length=255)),
                ('location', models.CharField(blank=True, default='', max_length=255)),
                ('logo_data', models.TextField(blank=True, default='')),
                ('layout', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_timemark_setting', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
    ]
