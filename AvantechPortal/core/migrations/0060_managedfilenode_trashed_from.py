from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_fundrequest_request_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='managedfilenode',
            name='trashed_from',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='trashed_children',
                to='core.managedfilenode',
            ),
        ),
    ]
