from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0130_erp_job_order_approval_and_payment_gates'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='erpprojectpipeline',
            name='project_head_responsible',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='erp_projects_led', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='erpprojectpipeline',
            name='disseminated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='erpprojectpipeline',
            name='disseminated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='erp_projects_disseminated', to=settings.AUTH_USER_MODEL),
        ),
    ]
