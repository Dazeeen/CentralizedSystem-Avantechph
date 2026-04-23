from django.db import migrations, models


def seed_default_item_types(apps, schema_editor):
    AssetItemType = apps.get_model('core', 'AssetItemType')
    AssetItem = apps.get_model('core', 'AssetItem')

    defaults = [
        {'name': 'Cable', 'code': 'cable', 'prefix': 'CBL', 'is_active': True},
        {'name': 'Laptop', 'code': 'laptop', 'prefix': 'LP', 'is_active': True},
        {'name': 'Other', 'code': 'other', 'prefix': 'AST', 'is_active': True},
    ]

    for payload in defaults:
        AssetItemType.objects.update_or_create(code=payload['code'], defaults=payload)

    existing_codes = set(
        AssetItemType.objects.values_list('code', flat=True)
    )

    for raw_item_type in AssetItem.objects.values_list('item_type', flat=True).distinct():
        code = (raw_item_type or '').strip().lower()
        if not code:
            continue
        if code in existing_codes:
            continue

        name = code.replace('-', ' ').replace('_', ' ').title()
        AssetItemType.objects.create(name=name, code=code, prefix='AST', is_active=True)
        existing_codes.add(code)


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_assetitem_asset_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetItemType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('code', models.SlugField(max_length=30, unique=True)),
                ('prefix', models.CharField(default='AST', max_length=5)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AlterField(
            model_name='assetitem',
            name='item_type',
            field=models.CharField(db_index=True, default='other', max_length=30),
        ),
        migrations.CreateModel(
            name='AssetItemImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='asset_images/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='images', to='core.assetitem')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.RunPython(seed_default_item_types, noop_reverse),
    ]
