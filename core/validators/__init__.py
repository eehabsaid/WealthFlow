from django.http import JsonResponse

from .ownership import (
    _owned_queryset,
    _owned_object_or_404,
    _child_owned_queryset,
    _child_owned_object_or_404,
)

def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    return None

__all__ = [
    "JsonResponse",
    "_owned_queryset",
    "_owned_object_or_404",
    "_child_owned_queryset",
    "_child_owned_object_or_404",
]
