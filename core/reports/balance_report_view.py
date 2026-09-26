# pyright: reportMissingTypeStubs=false, reportAssignmentType=false, reportRedeclaration=false
from django.views import View
from django.http import JsonResponse
from core.models import BalanceEntry, Bank
from core.services.balance.net_worth_service import NetWorthService
from core.services.shared.base_currency import get_user_base_code
from core.services.shared.currency_conversion_service import CurrencyConversionService
from core.validators import _api_auth_required

try:
    from core.views.certificate_views import _run_certificate_interest_sync
except (ImportError, ValueError):
    def _run_certificate_interest_sync(force: bool = False):
        return None

class BalanceReportView(View):
    """Balance summary across banks and currencies."""

    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error
        _run_certificate_interest_sync()

        entries = BalanceEntry.objects.select_related("bank", "currency").filter(owner=request.user)
        banks = Bank.objects.filter(owner=request.user)

        base_code = get_user_base_code(request.user)
        rates_to_base = CurrencyConversionService.get_rates_to_base(base_code)

        # Group by bank
        by_bank = []
        for bank in banks:
            bank_entries = list(entries.filter(bank=bank))
            # Was: filtered to currency__code="EGP" only, so any bank entry
            # held in a different currency silently never counted toward the
            # bank's total (and always showed 0 for a non-EGP-base account
            # holding no literal EGP). Now converts every entry to the
            # user's own base currency, matching what the frontend
            # (static/js/advanced_reports/balance.js) already labels this
            # field as: the bank's total in the base currency.
            total_base = sum(
                float(e.amount) * float(rates_to_base.get(e.currency.code, 0) if e.currency else 0)
                for e in bank_entries
            )
            by_bank.append(
                {
                    "bank_id": bank.id,
                    "bank_name": bank.name,
                    "total_egp": total_base,
                    "entries": [e.to_dict() for e in bank_entries],
                }
            )

        # Unbanked entries (cash / home)
        home = entries.filter(bank__isnull=True)
        by_currency = []
        for e in home:
            by_currency.append(e.to_dict())

        net_worth_data = NetWorthService(request.user).portfolio_components()
        cert_total = float(net_worth_data["certificate_total_egp"])
        cert_interest_total = float(net_worth_data["certificate_interest_total_egp"])

        cert_monthly_interest = cert_interest_total if cert_interest_total else 0.0

        return JsonResponse(
            {
                "by_bank": by_bank,
                "home_entries": by_currency,
                "cert_total": cert_total,
                "cert_interest": cert_monthly_interest,
                "cert_interest_total": cert_interest_total,
                "fixed_assets_total": float(net_worth_data["fixed_assets_total_egp"]),
                "net_worth": float(net_worth_data["net_worth_egp"]),
            }
        )
