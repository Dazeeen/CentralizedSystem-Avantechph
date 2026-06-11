from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0119_crmsalesrecord_proposal_data_and_more'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesactivitylog',
			name='quotation_proposal_inputs',
			field=models.JSONField(blank=True, default=dict),
		),
		migrations.AddField(
			model_name='crmsalesrecord',
			name='quotation_proposal_inputs',
			field=models.JSONField(blank=True, default=dict),
		),
	]
