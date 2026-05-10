from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0074_crmsalesactivityattachment'),
	]

	operations = [
		migrations.CreateModel(
			name='CRMSalesAgingSetting',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('aging_days', models.PositiveIntegerField(default=30)),
				('include_closed_won', models.BooleanField(default=False)),
				('updated_at', models.DateTimeField(auto_now=True)),
			],
			options={
				'verbose_name': 'CRM Sales Aging Setting',
				'verbose_name_plural': 'CRM Sales Aging Settings',
			},
		),
	]
