from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0072_crmsalesactivitylog'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesrecord',
			name='client_status',
			field=models.CharField(blank=True, max_length=80),
		),
		migrations.AddField(
			model_name='crmsalesrecord',
			name='interaction_notes',
			field=models.TextField(blank=True),
		),
	]
