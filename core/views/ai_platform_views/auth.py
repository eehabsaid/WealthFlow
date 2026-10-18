"""
Shared auth-check helpers for AI Platform views.

Split out of the former monolithic ai_platform_views.py (200-line rule).
"""

from django.http import JsonResponse

from core.authentication.utils.auth_utils import user_is_sysadmin


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


def _sysadmin_required(request):
    """401 when logged out, 403 for anyone who is not a system administrator."""
    auth_error = _api_auth_required(request)
    if auth_error:
        return auth_error
    if not user_is_sysadmin(request.user):
        return JsonResponse({"error": "Only a system administrator can change the AI knowledge base"}, status=403)
    return None
