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

def _expense_requires_bank(payment_method: str) -> bool:
    pm = str(payment_method or "").strip().lower()
    return pm in {"bank", "bank_transfer", "bank transfer", "card"}

def _expense_affects_balance(payment_method: str) -> bool:
    pm = str(payment_method or "").strip().lower()
    return pm in {"cash", "bank", "bank_transfer", "bank transfer", "card"}

def _asset_payment_requires_bank(payment_method: str) -> bool:
    pm = str(payment_method or "").strip().lower()
    return pm in {"bank", "bank transfer", "bank_transfer", "card"}

def _asset_payment_currency_required(payment_method: str) -> bool:
    pm = str(payment_method or "").strip().lower()
    return pm in {"cash", "bank", "bank transfer", "bank_transfer", "card"}

__all__ = [
    "JsonResponse",
    "_owned_queryset",
    "_owned_object_or_404",
    "_child_owned_queryset",
    "_child_owned_object_or_404",
]
