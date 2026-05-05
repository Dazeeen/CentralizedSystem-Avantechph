from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from types import MethodType


ROLE_PREVIEW_SESSION_KEY = "preview_role_id"
ROLE_PREVIEW_STOP_COOKIE = "role_preview_stopped"
ROLE_PREVIEW_ALLOWED_WRITE_PATHS = (
    "/logout/",
    "/roles/preview/stop/",
)
ROLE_PREVIEW_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def _is_role_preview_allowed_write(request):
    path = f"/{request.path_info.strip('/')}/"
    return any(path.endswith(allowed_path) for allowed_path in ROLE_PREVIEW_ALLOWED_WRITE_PATHS)


def _apply_role_preview(user, role):
    permission_names = {
        f"{permission.content_type.app_label}.{permission.codename}"
        for permission in role.permissions.select_related("content_type").all()
    }

    user._role_preview = {
        "role_id": role.id,
        "role_name": role.name,
        "permission_names": permission_names,
    }
    user.is_superuser = False
    user.is_staff = False

    for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        if hasattr(user, cache_name):
            delattr(user, cache_name)

    def has_perm(self, perm, obj=None):
        return bool(self.is_active and obj is None and perm in permission_names)

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj=obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        prefix = f"{app_label}."
        return any(permission_name.startswith(prefix) for permission_name in permission_names)

    def get_all_permissions(self, obj=None):
        if obj is not None or not self.is_active:
            return set()
        return set(permission_names)

    def get_group_permissions(self, obj=None):
        if obj is not None or not self.is_active:
            return set()
        return set(permission_names)

    user.has_perm = MethodType(has_perm, user)
    user.has_perms = MethodType(has_perms, user)
    user.has_module_perms = MethodType(has_module_perms, user)
    user.get_all_permissions = MethodType(get_all_permissions, user)
    user.get_group_permissions = MethodType(get_group_permissions, user)


class SessionInterruptedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except SessionInterrupted:
            return redirect("login")


class SafeSessionMiddleware(SessionMiddleware):
    def process_response(self, request, response):
        try:
            return super().process_response(request, response)
        except SessionInterrupted:
            return redirect("login")


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


class RolePreviewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.COOKIES.get(ROLE_PREVIEW_STOP_COOKIE):
                request.session.pop(ROLE_PREVIEW_SESSION_KEY, None)
                request.session.modified = True
                response = self.get_response(request)
                response.delete_cookie(ROLE_PREVIEW_STOP_COOKIE)
                return response

            role_id = request.session.get(ROLE_PREVIEW_SESSION_KEY)
            if role_id:
                try:
                    role = Group.objects.get(pk=role_id)
                except (Group.DoesNotExist, TypeError, ValueError):
                    request.session.pop(ROLE_PREVIEW_SESSION_KEY, None)
                    request.session.modified = True
                else:
                    request.role_preview_role = role
                    _apply_role_preview(request.user, role)
                    if (
                        request.method.upper() not in ROLE_PREVIEW_SAFE_METHODS
                        and not _is_role_preview_allowed_write(request)
                    ):
                        message = "Preview mode is read-only. Exit preview to perform this action."
                        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                            return JsonResponse({"ok": False, "message": message}, status=403)

                        messages.warning(request, message)
                        referer = (request.META.get("HTTP_REFERER") or "").strip()
                        if referer and url_has_allowed_host_and_scheme(referer, {request.get_host()}):
                            return redirect(referer)
                        return redirect("dashboard")

        return self.get_response(request)
