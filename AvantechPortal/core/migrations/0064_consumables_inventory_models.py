from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_backfill_collapsed_role_folders'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumableItemType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('code', models.SlugField(max_length=30, unique=True)),
                ('prefix', models.CharField(default='CON', max_length=5)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
                'permissions': [('view_consumablescategory', 'Can view consumables category')],
            },
        ),
        migrations.CreateModel(
            name='ConsumableItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=150)),
                ('item_type', models.CharField(db_index=True, default='other', max_length=30)),
                ('item_code', models.CharField(blank=True, max_length=20, unique=True)),
                ('code_prefix', models.CharField(blank=True, max_length=5)),
                ('specification', models.CharField(blank=True, max_length=255)),
                ('note', models.TextField(blank=True)),
                ('stock_quantity', models.PositiveIntegerField(default=0)),
                ('low_stock_threshold', models.PositiveIntegerField(default=5, help_text='Alert when stock falls below this level')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consumable_items_created', to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consumable_items', to='core.assetdepartment')),
            ],
            options={
                'ordering': ['item_code', 'item_name'],
            },
        ),
    ]
