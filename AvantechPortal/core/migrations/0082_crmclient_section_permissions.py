from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0081_crmclient_geo_latitude_crmclient_geo_longitude'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='crmclient',
            options={
                'ordering': ['-created_at'],
                'permissions': (
                    ('view_crm_dashboard', 'Can view CRM dashboard section'),
                    ('view_crm_clients_section', 'Can view CRM clients section'),
                    ('manage_crm_clients_section', 'Can manage CRM clients section'),
                    ('view_crm_sales_section', 'Can view CRM sales section'),
                    ('manage_crm_sales_section', 'Can manage CRM sales section'),
                    ('view_crm_technicals_section', 'Can view CRM technicals section'),
                    ('manage_crm_technicals_section', 'Can manage CRM technicals section'),
                ),
            },
        ),
    ]
