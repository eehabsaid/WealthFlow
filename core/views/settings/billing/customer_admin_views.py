"""Sysadmin customer view: list users with plan/status/trial/period/invoices and act on them.

Part of the settings/billing/ domain package; split further here if this grows past ~200 lines.
"""

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from core.services.billing import customer_admin_service as svc
from core.validators.json_body import parse_json_body
from core.views.auth_views import AdminRequiredMixin

User = get_user_model()


def _fail(exc: svc.CustomerAdminError):
    return JsonResponse({"error": exc.code, "message": exc.message}, status=exc.status)


class CustomerListView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse({"customers": svc.list_customers((request.GET.get("q") or "").strip())})


class CustomerActionView(AdminRequiredMixin, View):
    """POST {action: suspend|unsuspend|extend_trial|change_plan, days?, plan_id?}"""

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        data = parse_json_body(request)
        action = data.get("action")
        try:
            if action == "suspend":
                svc.suspend(user, request.user)
            elif action == "unsuspend":
                svc.unsuspend(user, request.user)
            elif action == "extend_trial":
                svc.extend_trial(user, data.get("days"))
            elif action == "change_plan":
                svc.change_plan(user, data.get("plan_id"))
            else:
                return JsonResponse({"error": "bad_action", "message": "Unknown action."}, status=400)
        except svc.CustomerAdminError as exc:
            return _fail(exc)
        return JsonResponse({"customer": svc.customer_dict(user)})


class InvoiceActionView(AdminRequiredMixin, View):
    """POST {action: mark_paid|void|refund, amount?, note?, revoke_access?}"""

    def post(self, request, invoice_id):
        data = parse_json_body(request)
        action = data.get("action")
        result = {}
        try:
            if action == "mark_paid":
                invoice = svc.mark_invoice_paid(invoice_id)
            elif action == "void":
                invoice = svc.void_invoice(invoice_id)
            elif action == "refund":
                result = svc.refund_invoice(
                    invoice_id,
                    amount=data.get("amount"),
                    note=str(data.get("note") or ""),
                    revoke_access=bool(data.get("revoke_access", True)),
                )
                invoice = None
            else:
                return JsonResponse({"error": "bad_action", "message": "Unknown action."}, status=400)
        except svc.CustomerAdminError as exc:
            return _fail(exc)
        owner_id = invoice.owner_id if invoice else result["invoice"]["owner_id"]
        owner = get_object_or_404(User, pk=owner_id)
        return JsonResponse({"customer": svc.customer_dict(owner), **{k: v for k, v in result.items() if k != "invoice"}})


class TrialOptionsView(AdminRequiredMixin, View):
    """Settings > Billing: give sysadmin-created users a trial (default ON)."""

    def get(self, request):
        from core.services.billing.trial_policy import admin_created_trial_enabled

        return JsonResponse({"trial_on_admin_created_users": admin_created_trial_enabled()})

    def put(self, request):
        from core.services.billing.trial_policy import admin_created_trial_enabled, set_admin_created_trial_enabled

        data = parse_json_body(request)
        if not isinstance(data.get("trial_on_admin_created_users"), bool):
            return JsonResponse({"error": "trial_on_admin_created_users must be true or false"}, status=400)
        set_admin_created_trial_enabled(data["trial_on_admin_created_users"])
        return JsonResponse({"trial_on_admin_created_users": admin_created_trial_enabled()})
