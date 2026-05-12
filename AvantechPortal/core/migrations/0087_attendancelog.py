from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('core', '0086_alter_crmclient_options_alter_loginevent_options_and_more'),
	]

	operations = [
		migrations.CreateModel(
			name='AttendanceLog',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('attendance_date', models.DateField(db_index=True)),
				('time_in_at', models.DateTimeField(blank=True, null=True)),
				('time_out_at', models.DateTimeField(blank=True, null=True)),
				('time_in_photo', models.ImageField(blank=True, null=True, upload_to='attendance/time_in/')),
				('time_out_photo', models.ImageField(blank=True, null=True, upload_to='attendance/time_out/')),
				('time_in_latitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
				('time_in_longitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
				('time_out_latitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
				('time_out_longitude', models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
				('time_in_location_label', models.CharField(blank=True, default='', max_length=255)),
				('time_out_location_label', models.CharField(blank=True, default='', max_length=255)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
				('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_logs', to=settings.AUTH_USER_MODEL)),
			],
			options={
				'ordering': ['-attendance_date', '-updated_at'],
				'constraints': [models.UniqueConstraint(fields=('user', 'attendance_date'), name='unique_user_attendance_day')],
			},
		),
	]
