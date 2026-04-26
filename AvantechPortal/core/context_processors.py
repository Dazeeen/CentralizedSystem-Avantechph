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


def finance_navigation_state(request):
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = getattr(resolver_match, 'url_name', '') or ''
    is_finance_nav_active = (
        url_name.startswith('finance_')
        or url_name.startswith('fund_request')
        or url_name.startswith('liquidation')
    )
    is_asset_tracker_nav_active = (
        url_name.startswith('assets_')
        or url_name.startswith('accountability')
    )
    return {
        'is_finance_nav_active': is_finance_nav_active,
        'is_asset_tracker_nav_active': is_asset_tracker_nav_active,
    }
