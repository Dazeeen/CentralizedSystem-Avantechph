from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0099_calculatorimportrecord_calculatorimportrow'),
	]

	operations = [
		migrations.AddField(
			model_name='calculatorimportrecord',
			name='is_active',
			field=models.BooleanField(db_index=True, default=False),
		),
	]
