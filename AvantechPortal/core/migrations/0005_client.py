from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_normalize_userprofile_status_choices'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=150)),
                ('exact_address', models.TextField()),
                ('active_phone_number', models.CharField(max_length=32)),
                ('email', models.EmailField(max_length=254)),
                ('average_monthly_electricity_bill', models.DecimalField(decimal_places=2, max_digits=12)),
                ('usage_of_electricity', models.CharField(choices=[('daytime', 'Daytime'), ('night', 'Night'), ('both', 'Both')], max_length=20)),
                ('appliances_and_electric_things', models.TextField()),
                ('property_status', models.CharField(choices=[('under_construction', 'Under Construction'), ('built', 'Built')], max_length=24)),
                ('client_type', models.CharField(choices=[('new', 'New Client'), ('old', 'Old Client')], default='new', max_length=8)),
                ('status', models.CharField(choices=[('inquiry', 'Inquiry'), ('quotation_sent', 'Quotation Sent'), ('negotiation', 'Negotiation'), ('closed_won', 'Closed Won'), ('closed_lost', 'Closed Lost')], default='inquiry', max_length=20)),
                ('handled_date', models.DateField(default=django.utils.timezone.localdate)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_clients', to=settings.AUTH_USER_MODEL)),
                ('handled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='handled_clients', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
