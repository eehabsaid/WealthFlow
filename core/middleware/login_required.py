"""Requires an authenticated session for every request except an explicit
public allowlist (login/signup/password-reset pages, the auth API, the
SPA shell, Django admin, and static/media assets).

This existed as a per-view convention (`_api_auth_required`) but many
view files never called it, so those endpoints were reachable without a
session. This middleware makes the gate unconditional and applies before
per-view/per-object ownership checks run.
"""

from django.http import JsonResponse
from django.shortcuts import redirect

EXEMPT_PATH_PREFIXES = (
    "/admin/",
    "/static/",
    "/media/",
    "/accounts/",
    "/api/auth/",
)

EXEMPT_PATHS = (
    "/",
    "/favicon.ico",
)


def _is_exempt(path: str) -> bool:
    if path in EXEMPT_PATHS:
        return True
    return path.startswith(EXEMPT_PATH_PREFIXES)


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _is_exempt(request.path) and not request.user.is_authenticated:
            if request.path.startswith("/api/"):
                return JsonResponse({"error": "Authentication required"}, status=401)
            return redirect("/accounts/login/")
        return self.get_response(request)
