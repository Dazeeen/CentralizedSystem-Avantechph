from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
		('core', '0122_ocular_time_window'),
	]

	operations = [
		migrations.CreateModel(
			name='CRMWarrantyDeletionRequest',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('warranty_number_snapshot', models.CharField(max_length=20)),
				('client_name_snapshot', models.CharField(max_length=220)),
				('reason', models.TextField(blank=True)),
				('requested_at', models.DateTimeField(auto_now_add=True)),
				('resubmission_count', models.PositiveIntegerField(default=0)),
				('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=20)),
				('reviewed_at', models.DateTimeField(blank=True, null=True)),
				('review_notes', models.TextField(blank=True)),
				('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crm_warranty_deletion_requests_created', to=settings.AUTH_USER_MODEL)),
				('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crm_warranty_deletion_requests_reviewed', to=settings.AUTH_USER_MODEL)),
				('warranty_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deletion_requests', to='core.crmwarrantyrecord')),
			],
			options={
				'ordering': ['-requested_at'],
				'permissions': [('approve_crmwarrantydeletionrequest', 'Can approve CRM warranty deletion requests')],
			},
		),
	]
