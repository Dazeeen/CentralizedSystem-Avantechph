from .models import Notification


def create_notification(user, title, message, link_url=''):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        link_url=link_url,
    )
