"""
Shared auth-check helper for AI Platform views.

Split out of the former monolithic ai_platform_views.py (200-line rule).
"""

from django.http import JsonResponse


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None
