from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0134_accountingrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='ac_wire_size_mm2',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='ats_breaker_size_at',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='ats_rating',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='ats_wire_size_mm2',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='battery_brand_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='battery_breaker_size',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='battery_capacity_ah',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='battery_wire_size_mm2',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='client_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='contact_number',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='coordinates',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='data_logger_serial_number',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='electrical_phase_type',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='email_address',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='establishment_type',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='full_address',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='installation_date_finished',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='installation_date_started',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='inverter_ac_breaker_size',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='inverter_brand_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='inverter_serial_number',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='inverter_size_kw',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='main_breaker_size_at',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='main_wire_size_mm2',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='monitoring_app_plant_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='panels_per_string',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='personnel_name_position',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='project_supervisor',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='pv_cable_size',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='pv_module_brand_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='pv_module_output_power_wp',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='pv_system_type_installed',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='rec_breaker_size_at',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='rec_wire_size_mm2',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='three_phase_voltage',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='total_panels',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='total_power_pv_system_kwp',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='crmtechnicalrecord',
            name='with_net_metering',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
