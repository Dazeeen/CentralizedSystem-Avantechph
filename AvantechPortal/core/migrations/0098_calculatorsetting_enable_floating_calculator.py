from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0097_calculatorsetting'),
	]

	operations = [
		migrations.AddField(
			model_name='calculatorsetting',
			name='enable_floating_calculator',
			field=models.BooleanField(default=True),
		),
	]

