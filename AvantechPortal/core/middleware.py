from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


class InactivityTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timeout_seconds = int(getattr(settings, "SESSION_TIMEOUT_SECONDS", settings.SESSION_COOKIE_AGE))
            now_ts = int(timezone.now().timestamp())
            last_seen_ts = request.session.get("last_activity_ts")

            if last_seen_ts and now_ts - int(last_seen_ts) > timeout_seconds:
                logout(request)
                request.session.flush()
                messages.warning(request, "You were automatically logged out due to inactivity.")
                return redirect("login")

            request.session["last_activity_ts"] = now_ts

        return self.get_response(request)
