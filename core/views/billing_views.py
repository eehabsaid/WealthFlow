from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from core.models import Plan
from core.services.billing import SubscriptionService


@login_required(login_url="/accounts/login/")
def billing_status(request):
    """Current user's subscription/trial state, for the trial banner + gating."""
    subscription = SubscriptionService.get_subscription(request.user)
    if subscription is None:
        return JsonResponse({"subscription": None, "has_access": request.user.is_superuser})
    # Touch has_active_access so an expired trial is flipped to "expired" immediately.
    has_access = SubscriptionService.has_active_access(request.user)
    subscription.refresh_from_db()
    data = subscription.to_dict()
    data["has_access"] = has_access
    return JsonResponse({"subscription": data})


@login_required(login_url="/accounts/login/")
def billing_plans(request):
    plans = Plan.objects.filter(is_active=True).order_by("sort_order", "id")
    return JsonResponse({"plans": [p.to_dict() for p in plans]})
