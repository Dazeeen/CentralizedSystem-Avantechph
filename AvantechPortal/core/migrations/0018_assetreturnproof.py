from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('core', '0017_userprofile_branch'),
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
	]

	operations = [
		migrations.CreateModel(
			name='AssetReturnProof',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('image', models.ImageField(upload_to='accountability_return_proofs/')),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('accountability', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_proofs', to='core.assetaccountability')),
				('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asset_return_proofs_uploaded', to=settings.AUTH_USER_MODEL)),
			],
			options={
				'ordering': ['-created_at'],
			},
		),
	]