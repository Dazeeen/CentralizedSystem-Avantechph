import logging

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .auth_utils import get_client_ip
from .models import LoginEvent, UserProfile

logger = logging.getLogger("auth_security")


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

    profile, _ = UserProfile.objects.get_or_create(user=user)
    suspicious = bool(profile.last_login_ip and profile.last_login_ip != ip_address)

    LoginEvent.objects.create(
        user=user,
        username_attempt=user.username,
        ip_address=ip_address,
        user_agent=user_agent,
        successful=True,
        reason="success",
    )

    profile.last_login_ip = ip_address
    profile.last_login_user_agent = user_agent
    profile.save(update_fields=["last_login_ip", "last_login_user_agent"])

    logger.info("Successful login user=%s ip=%s suspicious=%s", user.username, ip_address, suspicious)

    if suspicious and user.email:
        send_mail(
            subject="Avantech Portal security alert: new login location",
            message=(
                f"A login to your account was detected from a new IP address: {ip_address}.\n"
                "If this was not you, please reset your password immediately."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", "unknown")
    ip_address = get_client_ip(request) if request else "unknown"
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""

    LoginEvent.objects.create(
        username_attempt=username,
        ip_address=ip_address,
        user_agent=user_agent,
        successful=False,
        reason="invalid_credentials",
    )

    logger.warning("Failed login username=%s ip=%s", username, ip_address)


try:
    from axes.signals import user_locked_out

    @receiver(user_locked_out)
    def on_user_locked_out(sender, request, username, ip_address, **kwargs):
        lockout_ip = ip_address or get_client_ip(request)
        LoginEvent.objects.create(
            username_attempt=username,
            ip_address=lockout_ip,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255] if request else "",
            successful=False,
            reason="locked_out",
        )
        logger.error("User locked out username=%s ip=%s", username, lockout_ip)

        if username:
            User = get_user_model()
            user = User.objects.filter(username=username).first()
            if user and user.email:
                send_mail(
                    subject="Avantech Portal security alert: repeated login failures",
                    message=(
                        f"Multiple failed login attempts were detected for your account from IP: {lockout_ip}.\n"
                        "If this was not you, reset your password and review your account security settings."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
except Exception:
    pass
