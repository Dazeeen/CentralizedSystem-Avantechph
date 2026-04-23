from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_default_it_department(apps, schema_editor):
    AssetDepartment = apps.get_model('core', 'AssetDepartment')
    it_department, created = AssetDepartment.objects.get_or_create(
        name='IT',
        defaults={'is_default': True},
    )
    if not it_department.is_default:
        it_department.is_default = True
        it_department.save(update_fields=['is_default'])


def remove_default_it_department(apps, schema_editor):
    AssetDepartment = apps.get_model('core', 'AssetDepartment')
    AssetDepartment.objects.filter(name='IT').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_clientquotationdocument'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetDepartment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='AssetTagBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tag_batches', to='core.assetdepartment')),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asset_tag_batches_generated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AssetItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=150)),
                ('item_type', models.CharField(choices=[('cable', 'Cable'), ('laptop', 'Laptop'), ('other', 'Other')], default='other', max_length=20)),
                ('item_code', models.CharField(blank=True, max_length=20, unique=True)),
                ('code_prefix', models.CharField(blank=True, max_length=5)),
                ('specification', models.CharField(blank=True, max_length=255)),
                ('stock_quantity', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets_created', to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assets', to='core.assetdepartment')),
                ('parent_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='variants', to='core.assetitem')),
            ],
            options={
                'ordering': ['item_code', 'item_name'],
            },
        ),
        migrations.CreateModel(
            name='AssetTagEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag_code', models.CharField(max_length=30)),
                ('item_code_snapshot', models.CharField(max_length=20)),
                ('item_name_snapshot', models.CharField(max_length=150)),
                ('specification_snapshot', models.CharField(blank=True, max_length=255)),
                ('department_name_snapshot', models.CharField(max_length=100)),
                ('parent_item_code_snapshot', models.CharField(blank=True, max_length=20)),
                ('sequence', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='core.assettagbatch')),
                ('item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tag_entries', to='core.assetitem')),
            ],
            options={
                'ordering': ['item_code_snapshot', 'sequence'],
            },
        ),
        migrations.AddConstraint(
            model_name='assettagentry',
            constraint=models.UniqueConstraint(fields=('batch', 'tag_code'), name='unique_asset_tag_code_per_batch'),
        ),
        migrations.RunPython(create_default_it_department, remove_default_it_department),
    ]
