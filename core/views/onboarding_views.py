
from django.http import JsonResponse
from django.views import View

from core.validators.json_body import parse_json_body
from core.services.onboarding import OnboardingService
from core.validators import _api_auth_required

_ERROR_KEYS = {"invalid_amount": "onboarding_invalid_amount", "invalid_currency": "onboarding_invalid_currency"}


class OnboardingStatusView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        return JsonResponse(OnboardingService.status(request.user))


class OnboardingCompleteView(View):
    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            data = parse_json_body(request)
        except ValueError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        try:
            OnboardingService.complete(request.user, data if isinstance(data, dict) else {})
        except ValueError as exc:
            key = _ERROR_KEYS.get(str(exc), "onboarding_invalid_amount")
            return JsonResponse({"error": str(exc), "error_key": key}, status=400)
        return JsonResponse({"ok": True})
