import secrets

from django.conf import settings


def numeric_challenge():
    length = max(1, int(getattr(settings, 'CAPTCHA_LENGTH', 5) or 5))
    code = ''.join(secrets.choice('0123456789') for _ in range(length))
    return code, code
