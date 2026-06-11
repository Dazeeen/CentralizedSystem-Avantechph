from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0121_monthly_electric_bill_unit'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesactivitylog',
			name='ocular_end_time',
			field=models.TimeField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='crmsalesactivitylog',
			name='ocular_start_time',
			field=models.TimeField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='crmsalesrecord',
			name='ocular_end_time',
			field=models.TimeField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='crmsalesrecord',
			name='ocular_start_time',
			field=models.TimeField(blank=True, null=True),
		),
	]
