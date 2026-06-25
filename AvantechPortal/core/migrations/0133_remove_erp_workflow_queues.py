from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0132_erpdepartmentreadstate'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ERPDepartmentReadState',
        ),
        migrations.DeleteModel(
            name='ERPWorkflowEvent',
        ),
        migrations.DeleteModel(
            name='ERPProjectPipeline',
        ),
        migrations.DeleteModel(
            name='ERPWorkflowSetting',
        ),
    ]
