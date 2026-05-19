from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0095_alter_crmclient_options_alter_loginevent_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='crmsalesactivitylog',
            name='downpayment',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='crmsalesrecord',
            name='downpayment',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
