from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0084_forms_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formupload',
            name='subsection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='uploads', to='core.formsubsection'),
        ),
    ]
