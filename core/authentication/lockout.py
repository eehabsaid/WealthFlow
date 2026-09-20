"""Friendly lockout response for django-axes (429, translated error key)."""

from django.http import JsonResponse

from core.authentication.views.helpers import _render_auth

LOCKOUT_ERROR_KEY = "auth_error_too_many_attempts"


def lockout_response(request, credentials, *args, **kwargs):
    if request.path.startswith("/api/"):
        return JsonResponse({"error_key": LOCKOUT_ERROR_KEY, "error": LOCKOUT_ERROR_KEY}, status=429)
    response = _render_auth(
        request,
        "authentication/login.html",
        {"error_key": LOCKOUT_ERROR_KEY, "prefill_username": (credentials or {}).get("username", "")},
    )
    response.status_code = 429
    return response
