from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

	dependencies = [
		('core', '0073_crmsalesrecord_client_status_and_notes'),
	]

	operations = [
		migrations.CreateModel(
			name='CRMSalesActivityAttachment',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('file', models.FileField(upload_to=core.models.crm_sales_activity_attachment_upload_to)),
				('uploaded_at', models.DateTimeField(auto_now_add=True)),
				('activity_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='core.crmsalesactivitylog')),
			],
			options={
				'ordering': ['-uploaded_at'],
			},
		),
	]
