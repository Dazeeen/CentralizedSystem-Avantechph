from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0075_crmsalesagingsetting'),
	]

	operations = [
		migrations.AddField(
			model_name='crmsalesagingsetting',
			name='notify_remaining_days',
			field=models.PositiveIntegerField(default=5),
		),
	]
