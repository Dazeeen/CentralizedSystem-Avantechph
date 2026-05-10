from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('core', '0071_crmtechnicalrecord'),
	]

	operations = [
		migrations.CreateModel(
			name='CRMSalesActivityLog',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('client_status', models.CharField(blank=True, max_length=80)),
				('lead_source', models.CharField(blank=True, max_length=50)),
				('monthly_electric_bill', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
				('roof_type', models.CharField(blank=True, max_length=80)),
				('ownership', models.CharField(blank=True, max_length=20)),
				('project_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
				('return_on_investment', models.CharField(blank=True, max_length=80)),
				('sales_status', models.CharField(blank=True, max_length=50)),
				('interaction_notes', models.TextField(blank=True)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crm_sales_activity_logs_created', to=settings.AUTH_USER_MODEL)),
				('sales_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_logs', to='core.crmsalesrecord')),
			],
			options={
				'ordering': ['-created_at'],
			},
		),
	]
