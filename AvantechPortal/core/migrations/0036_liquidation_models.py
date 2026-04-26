from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_alter_fundrequest_request_status_cancelled'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LiquidationTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Liquidation Template', max_length=150)),
                ('file', models.FileField(upload_to=core.models.liquidation_template_upload_to)),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidation_templates_uploaded', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-is_active', '-updated_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Liquidation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('liquidation_date', models.DateField(default=django.utils.timezone.localdate)),
                ('branch', models.CharField(max_length=120)),
                ('position', models.CharField(blank=True, default='', max_length=120)),
                ('requested_by_name', models.CharField(max_length=150)),
                ('amount_requested', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('amount_returned_or_over', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidations_created', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidations', to='core.liquidationtemplate')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LiquidationLineItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_date', models.DateField()),
                ('fund_form_no', models.CharField(blank=True, default='', max_length=40)),
                ('description', models.CharField(max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('liquidation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='core.liquidation')),
                ('source_fund_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidation_items', to='core.fundrequest')),
                ('source_line_item', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidation_line_entry', to='core.fundrequestlineitem')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
