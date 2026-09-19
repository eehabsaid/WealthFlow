import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Currency, Plan
from core.services.billing import (
    CheckoutError,
    CheckoutService,
    PaymobGateway,
    SubscriptionService,
    UpgradeRequestService,
)

logger = logging.getLogger(__name__)


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
        currency = Currency.objects.filter(code=currency_code, owner=None).first()  # platform template — billing/plan currency is global, never per-user

    upgrade_request = UpgradeRequestService.submit(request.user, plan, currency)
    return JsonResponse({"upgrade_request": upgrade_request.to_dict()}, status=201)


@csrf_exempt
@login_required(login_url="/accounts/login/")
def billing_checkout(request):
    """Starts a real checkout for a priced plan. Returns either a Paymob
    iframe URL to redirect to, or fake/test mode when Paymob isn't
    configured yet (Settings > Billing Plans > Payment Gateway)."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body or "{}")
    plan = Plan.objects.filter(id=data.get("plan_id"), is_active=True).first()
    if plan is None:
        return JsonResponse({"error": "Plan not found."}, status=404)

    currency = Currency.objects.filter(code=data.get("currency_code"), owner=None).first()  # platform template — billing/plan currency is global, never per-user
    if currency is None:
        return JsonResponse({"error": "Currency not found."}, status=404)

    try:
        result = CheckoutService.initiate_checkout(request.user, plan, currency)
    except CheckoutError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(result, status=201)


@csrf_exempt
@login_required(login_url="/accounts/login/")
def billing_checkout_fake_complete(request):
    """Test-mode only: instantly completes a pending Invoice created while
    Paymob isn't configured. Stops responding the moment real Paymob keys
    are saved, so it can never be used to skip a real payment."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body or "{}")
    try:
        invoice = CheckoutService.complete_fake_payment(request.user, data.get("invoice_id"))
    except CheckoutError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"invoice": invoice.to_dict()})


@csrf_exempt
def paymob_webhook(request):
    """Paymob's server-to-server transaction-processed callback. Public
    (no login — Paymob calls this directly) but verified via HMAC."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    received_hmac = request.GET.get("hmac", "")
    if not PaymobGateway.verify_webhook_hmac(payload, received_hmac):
        logger.warning("Paymob webhook received with invalid or missing HMAC signature.")
        return JsonResponse({"error": "Invalid signature"}, status=403)

    CheckoutService.process_webhook(payload)
    return JsonResponse({"ok": True})
