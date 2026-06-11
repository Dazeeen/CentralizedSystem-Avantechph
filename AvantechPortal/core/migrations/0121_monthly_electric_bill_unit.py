from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0120_crmsalesrecord_quotation_proposal_inputs_and_more'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesactivitylog',
			name='monthly_electric_bill_unit',
			field=models.CharField(blank=True, default='kw', max_length=5),
		),
		migrations.AddField(
			model_name='crmsalesrecord',
			name='monthly_electric_bill_unit',
			field=models.CharField(blank=True, default='kw', max_length=5),
		),
	]
