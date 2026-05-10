from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0076_crmsalesagingsetting_notify_remaining_days'),
	]

	operations = [
		migrations.AddField(
			model_name='crmtechnicalrecord',
			name='installation_time',
			field=models.TimeField(blank=True, null=True),
		),
	]
