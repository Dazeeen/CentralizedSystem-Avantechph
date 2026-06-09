from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0116_crmwarrantyrecord'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesrecord',
			name='ocular_date',
			field=models.DateField(blank=True, db_index=True, null=True),
		),
		migrations.AddField(
			model_name='crmsalesactivitylog',
			name='ocular_date',
			field=models.DateField(blank=True, null=True),
		),
	]
