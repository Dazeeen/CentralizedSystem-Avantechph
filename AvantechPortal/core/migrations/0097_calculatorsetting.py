from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0096_crmsalesrecord_downpayment_and_log'),
	]

	operations = [
		migrations.CreateModel(
			name='CalculatorSetting',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('volt_drop_percent', models.DecimalField(decimal_places=2, default=3, max_digits=6)),
				('sun_peak_period_hours', models.DecimalField(decimal_places=2, default=4, max_digits=6)),
				('meralco_rate', models.DecimalField(decimal_places=4, default=0, max_digits=12)),
				('battery_health_protection_percent', models.DecimalField(decimal_places=2, default=20, max_digits=6)),
				('updated_at', models.DateTimeField(auto_now=True)),
			],
			options={
				'verbose_name': 'Calculator Settings',
				'verbose_name_plural': 'Calculator Settings',
			},
		),
	]
