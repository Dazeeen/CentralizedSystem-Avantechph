from django.db import migrations, models


def normalize_status_values(apps, schema_editor):
    UserProfile = apps.get_model('core', 'UserProfile')
    UserProfile.objects.filter(status='online').update(status='active')
    UserProfile.objects.filter(status='busy').update(status='idle')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_userprofile_avatar_userprofile_status'),
    ]

    operations = [
        migrations.RunPython(normalize_status_values, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='userprofile',
            name='status',
            field=models.CharField(
                choices=[('active', 'Active'), ('offline', 'Offline'), ('idle', 'Idle')],
                default='active',
                max_length=10,
            ),
        ),
    ]
