from .models import Notification


def notification_summary(request):
    if not request.user.is_authenticated:
        return {
            'notifications': [],
            'unread_notification_count': 0,
        }

    notifications = list(
        Notification.objects.filter(user=request.user, is_read=False)
        .order_by('-created_at')[:5]
    )
    unread_notification_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'notifications': notifications,
        'unread_notification_count': unread_notification_count,
    }
