import datetime
import time
from django.http import JsonResponse
from django.views import View

from core.models import Bank
from core.services.balance.net_worth_service import NetWorthService
from core.services.financial_advisor.cash_flow_forecast_service import CashFlowForecastService
from core.services.financial_advisor.cash_flow_forecast_service.custom_projection import compute_custom_cash_projection
from core.services.financial_advisor.commitments_calendar_service import CommitmentsCalendarService
from core.services.financial_advisor.portfolio_optimizer_service import PortfolioOptimizerService
from core.services.financial_advisor.wealth_growth_forecast_service import WealthGrowthForecastService
from core.services.financial_advisor.overview_service import OverviewService
from core.views.certificate_views import _run_certificate_interest_sync
from core.views.balance.forecasts.shared import _api_auth_required


class CertificateForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        return JsonResponse(NetWorthService(request.user).certificate_forecast_payload(today=datetime.date.today()))


class CashFlowForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = CashFlowForecastService(request.user, today=datetime.date.today()).payload()
        return JsonResponse(payload)


class CashFlowCustomProjectionView(View):
    """
    Interactive "what-if" cash projection: pick a target date, exclude
    specific recurring event types (salary, rental, mortgage, certificate
    events), choose EGP-only vs total-liquid currency scope. Backs the
    custom projection card in the Cash Flow tab. Pure deterministic
    computation — see custom_projection.py — never an LLM estimate.
    """

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()

        today = datetime.date.today()

        target_date_str = request.GET.get("target_date")
        if target_date_str:
            try:
                target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "invalid target_date, expected YYYY-MM-DD"}, status=400)
        else:
            days_param = request.GET.get("days")
            if days_param is not None:
                try:
                    days = int(days_param)
                except ValueError:
                    return JsonResponse(
                        {"error": f"invalid days value: {days_param!r}, expected an integer"}, status=400
                    )
            else:
                days = 30
            target_date = today + datetime.timedelta(days=max(1, days))

        if target_date <= today:
            return JsonResponse({"error": "target_date must be in the future"}, status=400)

        exclude_param = request.GET.get("exclude", "")
        exclude_types = [t.strip() for t in exclude_param.split(",") if t.strip()]

        currency_scope = request.GET.get("currency_scope", "base_only")

        payload = compute_custom_cash_projection(
            request.user,
            today=today,
            target_date=target_date,
            exclude_event_types=exclude_types,
            currency_scope=currency_scope,
        )
        return JsonResponse(payload)


class WealthGrowthForecastView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = WealthGrowthForecastService(request.user, today=datetime.date.today()).payload()
        return JsonResponse(payload)


class PortfolioOptimizerView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()
        payload = PortfolioOptimizerService(request.user, today=datetime.date.today()).payload()
        return JsonResponse(payload)


# Keyed by user id so one user's cached payload is never served to another
# — a bare module-level (payload, expiry) tuple would leak across users.
_overview_cache: dict = {}


class OverviewView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        now = time.time()
        cached = _overview_cache.get(request.user.id)
        if cached is not None:
            payload, expiry = cached
            if now < expiry:
                return JsonResponse(payload)

        _run_certificate_interest_sync()
        payload = OverviewService(request.user, today=datetime.date.today()).payload()

        _overview_cache[request.user.id] = (payload, now + 30.0)

        return JsonResponse(payload)


class CommitmentsCalendarView(View):
    """Financial Commitments Calendar: unified date-range event feed plus
    forecast-anchored liquidity analysis. Read-only — no posting, no
    balance changes. Month/week/agenda views are frontend rendering modes
    over this one payload."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        try:
            start_date = datetime.date.fromisoformat(request.GET.get("start_date", ""))
            end_date = datetime.date.fromisoformat(request.GET.get("end_date", ""))
        except ValueError:
            return JsonResponse({"error": "start_date and end_date must be YYYY-MM-DD"}, status=400)
        category = request.GET.get("category") or None
        if category and category not in ("income", "expense", "renewal"):
            return JsonResponse({"error": "invalid category"}, status=400)
        bank_id = None
        if request.GET.get("bank"):
            try:
                bank_id = int(request.GET.get("bank"))
            except ValueError:
                return JsonResponse({"error": "invalid bank"}, status=400)
            if not Bank.objects.filter(pk=bank_id, owner=request.user).exists():
                return JsonResponse({"error": "invalid bank"}, status=400)
        service = CommitmentsCalendarService(request.user, today=datetime.date.today())
        try:
            payload = service.payload(start_date, end_date, category=category, bank_id=bank_id)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        return JsonResponse(payload)
