from core.views.certificate_views import _run_certificate_interest_sync
# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render
from core.models import (
    SalaryEntry,
    BalanceEntry,
    AppSettings,
    BankCertificate,
    ReminderRule,
    ReminderLog,

)

import datetime
from core.services.balance.net_worth_service import NetWorthService

User = get_user_model()

if not __name__.endswith('.auth_views') and not __name__ == 'core.views.auth_views':
    try:
        pass
    except (ImportError, ValueError):
        pass

def _parse_iso_date(value):
    if not value:
        return None
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return value
    return value

@login_required(login_url="/accounts/login/")
def index(request):
    return render(request, "index.html")

def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None

@method_decorator(csrf_exempt, name="dispatch")
class DashboardSummaryView(View):
    """Enhanced dashboard summary — salary KPIs + cert maturity + balance."""

    def get(self, request):
        _run_certificate_interest_sync()
        from datetime import date, timedelta
        from django.db.models import Sum, Count, Q

        today = date.today()

        # Salary grand totals
        sal_agg = SalaryEntry.objects.aggregate(
            total_paid=Sum("paid"),
            total_bonus=Sum("bonus"),
            total_expected=Sum("expected"),
            paid_months=Count("id", filter=Q(paid__gt=0)),
        )

        # Certificates
        certs = BankCertificate.objects.select_related("bank").all()
        cert_agg = certs.aggregate(
            total=Sum("amount"),
            total_interest=Sum("interest_value"),
        )
        expiring_soon_days = int(AppSettings.get("cert_expiry_warning_days", "30"))
        expiring_soon = list(
            certs.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + timedelta(days=expiring_soon_days),
            )
            .order_by("expiry_date")
            .values("id", "expiry_date", "amount", "status", "bank__name")
        )
        for e in expiring_soon:
            e["days_left"] = (e["expiry_date"] - today).days
            e["expiry_date"] = e["expiry_date"].isoformat()

        # Active reminders (due today)
        active_reminders = []
        for rule in ReminderRule.objects.filter(
            is_active=True, rule_type="cert_maturity"
        ):
            logs = ReminderLog.objects.filter(rule=rule, fired_on=today).values(
                "message", "related_id", "related_model"
            )
            for l in logs:
                active_reminders.append({"rule": rule.name, "message": l["message"]})

        # Balance
        bal_entries = BalanceEntry.objects.select_related("currency").all()
        egp_balance = float(
            bal_entries.filter(currency__code="EGP").aggregate(s=Sum("amount"))["s"]
            or 0
        )

        net_worth = NetWorthService().portfolio_components()

        return JsonResponse(
            {
                "salary": {
                    "total_paid": float(sal_agg["total_paid"] or 0),
                    "total_bonus": float(sal_agg["total_bonus"] or 0),
                    "total_expected": float(sal_agg["total_expected"] or 0),
                    "paid_months": sal_agg["paid_months"] or 0,
                },
                "certificates": {
                    "total_amount": float(cert_agg["total"] or 0),
                    "total_interest": float(cert_agg["total_interest"] or 0),
                    "monthly_interest": float(cert_agg["total_interest"] or 0),
                    "count": certs.count(),
                },
                "expiring_soon": expiring_soon,
                "active_reminders": active_reminders,
                "egp_balance": egp_balance,
                "expiry_warning_days": expiring_soon_days,
                "net_worth": {
                    "total": float(net_worth["net_worth_egp"]),
                    "liquid_assets": float(net_worth["liquid_assets_total_egp"]),
                    "fixed_assets": float(net_worth["fixed_assets_total_egp"]),
                },
            }
        )

