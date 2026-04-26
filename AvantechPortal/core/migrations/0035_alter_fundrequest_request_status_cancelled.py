from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_alter_databasefile_file_fundrequestattachment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fundrequest',
            name='request_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending Approval'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('cancelled', 'Cancelled'),
                ],
                db_index=True,
                default='pending',
                max_length=20,
            ),
        ),
    ]
