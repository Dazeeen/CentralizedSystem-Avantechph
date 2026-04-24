from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_fundrequest_fundrequestlineitem_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='fundrequest',
            name='request_year',
            field=models.PositiveIntegerField(blank=True, db_index=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='fundrequest',
            name='serial_number',
            field=models.CharField(blank=True, editable=False, max_length=9, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='fundrequest',
            name='serial_sequence',
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='fundrequest',
            name='decision_reason',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fundrequest',
            name='processed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='fundrequest',
            name='processed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fund_requests_processed', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='fundrequest',
            name='request_status',
            field=models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='approved', max_length=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='fundrequest',
            name='request_status',
            field=models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=20),
        ),
    ]
