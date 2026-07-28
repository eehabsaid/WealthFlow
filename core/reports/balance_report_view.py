# pyright: reportMissingTypeStubs=false, reportAssignmentType=false, reportRedeclaration=false
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum
from core.models import BalanceEntry, Bank
from core.services.balance.net_worth_service import NetWorthService

try:
    from core.views.certificate_views import _run_certificate_interest_sync
except (ImportError, ValueError):
    def _run_certificate_interest_sync(force: bool = False):
        return None

@method_decorator(csrf_exempt, name="dispatch")
class BalanceReportView(View):
    """Balance summary across banks and currencies."""

    def get(self, request):
        _run_certificate_interest_sync()

        entries = BalanceEntry.objects.select_related("bank", "currency").all()
        banks = Bank.objects.all()

        # Group by bank
        by_bank = []
        for bank in banks:
            bank_entries = entries.filter(bank=bank)
            total_egp = float(
                bank_entries.filter(currency__code="EGP").aggregate(s=Sum("amount"))[
                    "s"
                ]
                or 0
            )
            by_bank.append(
                {
                    "bank_id": bank.id,
                    "bank_name": bank.name,
                    "total_egp": total_egp,
                    "entries": [e.to_dict() for e in bank_entries],
                }
            )

        # Unbanked entries (cash / home)
        home = entries.filter(bank__isnull=True)
        by_currency = []
        for e in home:
            by_currency.append(e.to_dict())

        net_worth_data = NetWorthService().portfolio_components()
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
