import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Currency, Plan
from core.services.billing import SubscriptionService, UpgradeRequestService


@login_required(login_url="/accounts/login/")
def billing_status(request):
    """Current user's subscription/trial state, for the trial banner + gating."""
    subscription = SubscriptionService.get_subscription(request.user)
    pending_request = UpgradeRequestService.get_pending(request.user)
    pending_data = pending_request.to_dict() if pending_request else None

    if subscription is None:
        return JsonResponse(
            {
                "subscription": None,
                "has_access": request.user.is_superuser,
                "pending_upgrade_request": pending_data,
            }
        )
    # Touch has_active_access so an expired trial is flipped to "expired" immediately.
    has_access = SubscriptionService.has_active_access(request.user)
    subscription.refresh_from_db()
    data = subscription.to_dict()
    data["has_access"] = has_access
    return JsonResponse({"subscription": data, "pending_upgrade_request": pending_data})


@login_required(login_url="/accounts/login/")
def billing_plans(request):
    plans = Plan.objects.filter(is_active=True).order_by("sort_order", "id")
    return JsonResponse({"plans": [p.to_dict() for p in plans]})


@csrf_exempt
@login_required(login_url="/accounts/login/")
def billing_upgrade_request(request):
    """Customer-submitted "I want to upgrade" intent. There's no live
    gateway checkout yet, so this just records the request for Ehab to
    follow up on manually (admin-visible via backup/export for now)."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body or "{}")
    plan_id = data.get("plan_id")
    plan = Plan.objects.filter(id=plan_id, is_active=True).first()
    if plan is None:
        return JsonResponse({"error": "Plan not found."}, status=404)

    currency = None
    currency_code = data.get("currency_code")
    if currency_code:
        currency = Currency.objects.filter(code=currency_code).first()

    upgrade_request = UpgradeRequestService.submit(request.user, plan, currency)
    return JsonResponse({"upgrade_request": upgrade_request.to_dict()}, status=201)
