from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
		('core', '0115_crmtechnicalrecord_job_order_number'),
	]

	operations = [
		migrations.CreateModel(
			name='CRMWarrantyRecord',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('warranty_number', models.CharField(db_index=True, max_length=20, unique=True)),
				('product_system', models.CharField(blank=True, max_length=120)),
				('warranty_type', models.CharField(choices=[('product', 'Product'), ('labor', 'Labor'), ('performance', 'Performance'), ('service', 'Service')], max_length=20)),
				('start_date', models.DateField()),
				('end_date', models.DateField()),
				('exclusions', models.TextField(blank=True)),
				('notes', models.TextField(blank=True)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
				('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='warranty_records', to='core.crmclient')),
				('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crm_warranty_records_created', to=settings.AUTH_USER_MODEL)),
				('sales_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='warranty_records', to='core.crmsalesrecord')),
				('technical_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='warranty_records', to='core.crmtechnicalrecord')),
			],
			options={
				'ordering': ['-created_at', '-id'],
			},
		),
	]
