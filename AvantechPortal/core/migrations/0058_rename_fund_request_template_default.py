from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_merge_ticketing_and_file_manager'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fundrequest',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Payment Request',
                'verbose_name_plural': 'Payment Requests',
            },
        ),
        migrations.AlterModelOptions(
            name='fundrequestattachment',
            options={
                'ordering': ['id'],
                'verbose_name': 'Payment Request Attachment',
                'verbose_name_plural': 'Payment Request Attachments',
            },
        ),
        migrations.AlterModelOptions(
            name='fundrequestautoapproverule',
            options={
                'ordering': ['-is_active', '-updated_at', '-created_at'],
                'verbose_name': 'Payment Request Auto-Approve Rule',
                'verbose_name_plural': 'Payment Request Auto-Approve Rules',
            },
        ),
        migrations.AlterModelOptions(
            name='fundrequestlineitem',
            options={
                'ordering': ['id'],
                'verbose_name': 'Payment Request Line Item',
                'verbose_name_plural': 'Payment Request Line Items',
            },
        ),
        migrations.AlterModelOptions(
            name='fundrequesttemplate',
            options={
                'ordering': ['-is_active', '-updated_at', '-created_at'],
                'verbose_name': 'Payment Request Template',
                'verbose_name_plural': 'Payment Request Templates',
            },
        ),
        migrations.AlterField(
            model_name='fundrequesttemplate',
            name='name',
            field=models.CharField(default='Payment Request Template', max_length=150),
        ),
    ]
