from django.db import migrations


def recompute_profile_completed(apps, schema_editor):
	UserProfile = apps.get_model('core', 'UserProfile')
	for profile in UserProfile.objects.select_related('user').all():
		user = profile.user
		profile.profile_completed = all([
			(user.first_name or '').strip(),
			(user.last_name or '').strip(),
			(user.email or '').strip(),
			(profile.contact_number or '').strip(),
		])
		profile.save(update_fields=['profile_completed'])


class Migration(migrations.Migration):

	dependencies = [
		('core', '0124_userprofile_profile_completed'),
	]

	operations = [
		migrations.RunPython(recompute_profile_completed, migrations.RunPython.noop),
	]
