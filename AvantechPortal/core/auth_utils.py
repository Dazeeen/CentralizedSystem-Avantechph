import logging

from django.contrib.sessions.models import Session

logger = logging.getLogger("auth_security")


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def invalidate_user_sessions(user):
    user_id = str(user.pk)
    deleted = 0

    for session in Session.objects.all():
        data = session.get_decoded()
        if data.get("_auth_user_id") == user_id:
            session.delete()
            deleted += 1

    logger.info("Invalidated %s sessions for user_id=%s", deleted, user_id)
    return deleted
