from functools import wraps

from django.http import JsonResponse

from core.services.billing.subscription_service import SubscriptionService


def subscription_required(view_func):
    """Blocks access once a trial/subscription has lapsed. Does not check plan tier."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not SubscriptionService.has_active_access(request.user):
            return JsonResponse(
                {"error": "subscription_required", "message": "Your trial or subscription has ended."},
                status=402,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


def plan_required(plan_code: str):
    """Blocks access unless the user's subscription is on `plan_code` or higher."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not SubscriptionService.plan_allows(request.user, plan_code):
                return JsonResponse(
                    {"error": "plan_upgrade_required", "required_plan": plan_code},
                    status=402,
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
