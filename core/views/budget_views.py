# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from django.http import JsonResponse
from django.views import View

from core.models import Budget, RecurringTransaction, BUDGET_PERIOD_CHOICES, RECURRING_FREQUENCY_CHOICES
from core.validators import _api_auth_required, _owned_queryset, _owned_object_or_404
from core.validators.json_body import parse_json_body

CURRENCY_ERROR_KEYS = {
    "exchange_rate_missing": ("No exchange rate exists for the selected currency", 400),
}


def _currency_error_response(exc):
    key = str(exc)
    if key in CURRENCY_ERROR_KEYS:
        message, status = CURRENCY_ERROR_KEYS[key]
        return JsonResponse({"error": message, "error_key": key}, status=status)
    return None


class BudgetListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.budgets import BudgetService

        return JsonResponse({
            "budgets": BudgetService.list_with_spend(request.user),
            "periods": [{"value": v, "label": l} for v, l in BUDGET_PERIOD_CHOICES],
        })

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = parse_json_body(request)
        from core.services.budgets import BudgetService

        try:
            budget = BudgetService.create_budget(data, request.user)
        except ValueError as exc:
            err = _currency_error_response(exc)
            if err:
                return err
            raise
        return JsonResponse(budget.to_dict(), status=201)


class BudgetDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        budget = _owned_object_or_404(Budget, pk, request)
        data = parse_json_body(request)
        from core.services.budgets import BudgetService

        try:
            budget = BudgetService.update_budget(budget, data)
        except ValueError as exc:
            err = _currency_error_response(exc)
            if err:
                return err
            raise
        return JsonResponse(budget.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        budget = _owned_object_or_404(Budget, pk, request)
        budget.delete()
        return JsonResponse({"deleted": True})


class RecurringTransactionListView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        recs = _owned_queryset(RecurringTransaction, request).select_related("category", "currency", "bank")
        return JsonResponse({
            "recurring_transactions": [r.to_dict() for r in recs],
            "frequencies": [{"value": v, "label": l} for v, l in RECURRING_FREQUENCY_CHOICES],
        })

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        data = parse_json_body(request)
        from core.services.budgets import RecurringService

        rec = RecurringService.create_recurring(data, request.user)
        return JsonResponse(rec.to_dict(), status=201)


class RecurringTransactionDetailView(View):
    def put(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        rec = _owned_object_or_404(RecurringTransaction, pk, request)
        data = parse_json_body(request)
        from core.services.budgets import RecurringService

        rec = RecurringService.update_recurring(rec, data)
        return JsonResponse(rec.to_dict())

    def delete(self, request, pk):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        rec = _owned_object_or_404(RecurringTransaction, pk, request)
        rec.delete()
        return JsonResponse({"deleted": True})


class RecurringTransactionDuePreviewView(View):
    """Read-only: what "Post Due Now" would post. Writes nothing."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.budgets import RecurringService

        return JsonResponse({"due": RecurringService.preview_due(request.user)})


class RecurringTransactionProcessDueView(View):
    """Manually trigger posting of any due recurring transactions for the
    logged-in user (also safe to call from a periodic scheduler job)."""

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.budgets import RecurringService

        created, skipped = RecurringService.process_due(request.user)
        return JsonResponse({
            "created": [e.to_dict() for e in created],
            "skipped": skipped,
        })


class BudgetAlertsView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        from core.services.budgets import AlertService

        return JsonResponse({"alerts": AlertService.get_alerts(request.user)})
