from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0117_crmsalesrecord_ocular_date_and_more'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesactivitylog',
			name='service_type',
			field=models.CharField(blank=True, max_length=30),
		),
		migrations.AddField(
			model_name='crmsalesrecord',
			name='service_type',
			field=models.CharField(blank=True, choices=[('solar', 'Solar'), ('hvac', 'HVAC'), ('security', 'Security Solutions')], max_length=30),
		),
	]
