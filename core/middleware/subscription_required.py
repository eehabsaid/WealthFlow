"""Blocks the data API once a user's trial/subscription has lapsed.

Before this existed the "Your trial has ended" banner was cosmetic: only the AI workspace endpoints were
gated (by plan feature flag), so a user with an expired trial could keep using every other endpoint.

A lapsed user gets HTTP 402 {"error": "subscription_required"} on every /api/ request except what is needed to
sign out, see their plan and upgrade/pay (and to render the shell). Superusers, sysadmins and users with no
subscription row are never blocked (see SubscriptionService.is_lapsed). Non-/api/ routes carry no user data:
the SPA shell, auth/legal pages and the Paymob return page stay reachable so the upgrade page can load.
"""

from django.http import JsonResponse

from core.services.billing.subscription_service import SubscriptionService

# Always reachable for a lapsed user: auth (login/logout/me/profile), billing (status, plans, upgrade request,
# checkout, Paymob webhook) and /api/account/ (own-data export / account deletion).
EXEMPT_API_PREFIXES = ("/api/auth/", "/api/billing/", "/api/account/")
# Read-only: the shell loads language/theme preferences from here on start-up.
EXEMPT_API_GET_PATHS = ("/api/settings/",)


def _exempt(request) -> bool:
    path = request.path
    if path.startswith(EXEMPT_API_PREFIXES):
        return True
    return request.method in ("GET", "HEAD") and path in EXEMPT_API_GET_PATHS


class SubscriptionRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith("/api/")
            and request.user.is_authenticated
            and not _exempt(request)
            and SubscriptionService.is_lapsed(request.user)
        ):
            return JsonResponse(
                {"error": "subscription_required", "message": "Your trial or subscription has ended."},
                status=402,
            )
        return self.get_response(request)
