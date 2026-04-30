from .auth_utils import get_client_ip
from .models import ActivityLog


def _actor_from_request(request):
	user = getattr(request, 'user', None)
	if user and getattr(user, 'is_authenticated', False):
		return user
	return None


def record_activity(request, action, category, summary, target=None, target_label='', metadata=None):
	actor = _actor_from_request(request)
	resolver_match = getattr(request, 'resolver_match', None)
	ip_address = get_client_ip(request) if request is not None else None
	if ip_address == 'unknown':
		ip_address = None
	target_model = ''
	target_id = ''
	if target is not None:
		target_model = target.__class__.__name__
		target_pk = getattr(target, 'pk', None)
		target_id = str(target_pk) if target_pk is not None else ''
		if not target_label:
			target_label = str(target)

	user_agent = ''
	if request is not None:
		user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:255]

	return ActivityLog.objects.create(
		actor=actor,
		action=action,
		category=category,
		summary=summary[:255],
		target_model=target_model[:120],
		target_id=target_id[:64],
		target_label=(target_label or '')[:255],
		url_name=(getattr(resolver_match, 'url_name', '') or '')[:120],
		path=(getattr(request, 'path', '') or '')[:255] if request is not None else '',
		ip_address=ip_address,
		user_agent=user_agent,
		metadata=metadata or {},
	)
