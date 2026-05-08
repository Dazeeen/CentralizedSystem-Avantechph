from datetime import date

from django.db import migrations, models


def backfill_crmclient_email_dob(apps, schema_editor):
    CRMClient = apps.get_model('core', 'CRMClient')
    fallback_dob = date(1970, 1, 1)

    for client in CRMClient.objects.all().only('id', 'email', 'date_of_birth'):
        changed_fields = []
        if not (client.email or '').strip():
            client.email = f'legacy-client-{client.id}@placeholder.local'
            changed_fields.append('email')
        if client.date_of_birth is None:
            client.date_of_birth = fallback_dob
            changed_fields.append('date_of_birth')
        if changed_fields:
            client.save(update_fields=changed_fields)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0067_crmclient_notes'),
    ]

    operations = [
        migrations.RunPython(backfill_crmclient_email_dob, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='crmclient',
            name='date_of_birth',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='crmclient',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AddConstraint(
            model_name='crmclient',
            constraint=models.CheckConstraint(
                condition=~models.Q(email=''),
                name='crmclient_email_not_blank',
            ),
        ),
    ]
