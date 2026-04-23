from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse


def axes_lockout_response(request, credentials=None, *args, **kwargs):
    username = ''
    if credentials and isinstance(credentials, dict):
        username = (credentials.get('username') or '').strip()[:150]

    query = urlencode({'u': username}) if username else ''
    lockout_url = reverse('lockout_notice')
    if query:
        lockout_url = f'{lockout_url}?{query}'

    return redirect(lockout_url)
