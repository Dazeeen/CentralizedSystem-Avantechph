from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0098_calculatorsetting_enable_floating_calculator'),
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
	]

	operations = [
		migrations.CreateModel(
			name='CalculatorImportRecord',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('source_file', models.FileField(upload_to=core.models.calculator_import_upload_to)),
				('original_filename', models.CharField(max_length=255)),
				('file_size_bytes', models.PositiveBigIntegerField(default=0)),
				('headers', models.JSONField(blank=True, default=list)),
				('included_headers', models.JSONField(blank=True, default=list)),
				('column_mappings', models.JSONField(blank=True, default=dict)),
				('row_count', models.PositiveIntegerField(default=0)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
				('imported_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='calculator_import_records', to=settings.AUTH_USER_MODEL)),
			],
			options={
				'ordering': ['-created_at'],
			},
		),
		migrations.CreateModel(
			name='CalculatorImportRow',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('system_type', models.CharField(blank=True, default='', max_length=255)),
				('capacity_kw', models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True)),
				('upgrade_brands', models.CharField(blank=True, default='', max_length=255)),
				('specifications', models.TextField(blank=True, default='')),
				('battery_ampere_hour', models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True)),
				('battery_kwh', models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True)),
				('warranty_panel', models.CharField(blank=True, default='', max_length=255)),
				('warranty_battery', models.CharField(blank=True, default='', max_length=255)),
				('warranty_inverter', models.CharField(blank=True, default='', max_length=255)),
				('panel_qty', models.PositiveIntegerField(blank=True, null=True)),
				('regular_price', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
				('cash_promo_price', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
				('bdo_installment_12mos', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
				('bdo_installment_18mos', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
				('bdo_installment_24mos', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
				('potential_monthly_savings', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
				('potential_annual_savings', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
				('potential_roi', models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
				('raw_row', models.JSONField(blank=True, default=dict)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('import_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rows', to='core.calculatorimportrecord')),
			],
			options={
				'ordering': ['id'],
			},
		),
	]
