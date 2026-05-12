from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0083_crmtechnicalrecord_net_metering_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FormSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forms_sections_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='FormSubsection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forms_subsections_created', to=settings.AUTH_USER_MODEL)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subsections', to='core.formsection')),
            ],
            options={'ordering': ['section__name', 'name']},
        ),
        migrations.CreateModel(
            name='FormUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=core.models.forms_file_upload_to)),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('file_size', models.PositiveBigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='uploads', to='core.formsection')),
                ('subsection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='uploads', to='core.formsubsection')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forms_uploads', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['section__name', 'subsection__name', '-created_at']},
        ),
        migrations.AddConstraint(
            model_name='formsubsection',
            constraint=models.UniqueConstraint(fields=('section', 'name'), name='unique_form_subsection_per_section'),
        ),
    ]
