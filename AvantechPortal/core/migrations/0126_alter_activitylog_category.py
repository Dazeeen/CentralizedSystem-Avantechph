from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0125_recompute_profile_completed'),
	]

	operations = [
		migrations.AlterField(
			model_name='activitylog',
			name='category',
			field=models.CharField(choices=[('clients', 'Clients'), ('finance', 'Accounting'), ('assets', 'Asset Tracker'), ('accountability', 'Accountability'), ('support', 'Support Tickets'), ('development', 'Development'), ('file_manager', 'File Manager'), ('backup', 'Backups'), ('system', 'System'), ('users', 'Users & Roles'), ('security', 'Security')], db_index=True, max_length=32),
		),
	]
