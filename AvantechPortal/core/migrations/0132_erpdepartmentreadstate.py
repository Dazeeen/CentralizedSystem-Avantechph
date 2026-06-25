from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0131_erp_job_order_dissemination'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ERPDepartmentReadState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(choices=[('sales', 'Sales'), ('accounting', 'Accounting'), ('procurement', 'Procurement'), ('inventory', 'Inventory'), ('technical', 'Technical'), ('quality', 'Quality'), ('aftersales', 'Aftersales')], max_length=20)),
                ('last_seen_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='erp_department_read_states', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='erpdepartmentreadstate',
            constraint=models.UniqueConstraint(fields=('user', 'department'), name='unique_erp_department_read_state'),
        ),
    ]
