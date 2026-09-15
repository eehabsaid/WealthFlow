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


def feature_required(feature_flag: str):
    """Blocks access unless the user's current Plan has `feature_flag` set
    (e.g. `feature_required("allows_ai_workspace")`). Unlike `plan_required`,
    this never references a specific plan code/tier — admins toggle the
    flag per plan from the Billing Plans settings tab."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not SubscriptionService.plan_allows_feature(request.user, feature_flag):
                return JsonResponse(
                    {"error": "plan_upgrade_required", "required_feature": feature_flag},
                    status=402,
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


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
