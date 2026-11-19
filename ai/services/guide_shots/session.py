"""A short-lived login session for the capture browser, created for the user the guide is written for (never a password)."""

from __future__ import annotations

from contextlib import contextmanager
from importlib import import_module

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY


def _backend() -> str:
    """The first configured backend that can load a user from a session (the rate-limit wrapper in front of it cannot)."""
    from django.utils.module_loading import import_string

    for path in settings.AUTHENTICATION_BACKENDS:
        if hasattr(import_string(path), "get_user"):
            return path
    return settings.AUTHENTICATION_BACKENDS[0]


@contextmanager
def session_cookie(user):
    """Yields {"name", "value"} of a fresh session of `user`; the session is deleted afterwards."""
    store = import_module(settings.SESSION_ENGINE).SessionStore()
    store[SESSION_KEY] = user._meta.pk.value_to_string(user)
    store[BACKEND_SESSION_KEY] = _backend()
    store[HASH_SESSION_KEY] = user.get_session_auth_hash()
    store.save()
    try:
        yield {"name": settings.SESSION_COOKIE_NAME, "value": store.session_key}
    finally:
        try:
            store.delete()
        except Exception:   # noqa: BLE001 - an expired-anyway session must not break the guide
            pass
