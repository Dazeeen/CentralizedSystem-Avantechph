from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0118_crmsalesrecord_service_type_and_more'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesactivitylog',
			name='proposal_data',
			field=models.JSONField(blank=True, default=dict),
		),
		migrations.AddField(
			model_name='crmsalesrecord',
			name='proposal_data',
			field=models.JSONField(blank=True, default=dict),
		),
	]
