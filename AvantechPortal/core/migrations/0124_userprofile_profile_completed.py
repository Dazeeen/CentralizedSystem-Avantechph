from django.db import migrations, models


def mark_existing_completed_profiles(apps, schema_editor):
	UserProfile = apps.get_model('core', 'UserProfile')
	for profile in UserProfile.objects.select_related('user').all():
		user = profile.user
		is_complete = all([
			(user.first_name or '').strip(),
			(user.last_name or '').strip(),
			(user.email or '').strip(),
			(profile.contact_number or '').strip(),
		])
		if is_complete:
			profile.profile_completed = True
			profile.save(update_fields=['profile_completed'])


class Migration(migrations.Migration):

	dependencies = [
		('core', '0123_crmwarrantydeletionrequest'),
	]

	operations = [
		migrations.AddField(
			model_name='userprofile',
			name='profile_completed',
			field=models.BooleanField(default=False),
		),
		migrations.RunPython(mark_existing_completed_profiles, migrations.RunPython.noop),
	]
