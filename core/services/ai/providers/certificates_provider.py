"""
Bank Certificates Data Provider for AI business context. Read-only.
"""

from __future__ import annotations

from typing import Any
from core.models import BankCertificate
from core.services.ai.providers.base import BaseContextProvider


class BankCertificatesDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "bank_certificates"

    @property
    def name(self) -> str:
        return "Bank Investment Certificates"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Investment Certificate Yield & Maturity Tracking",
            "provided_by": "BankCertificatesDataProvider",
            "consumes": ["BankCertificate", "BankCertificateInterestHistory"],
            "used_by": ["Portfolio", "Opportunities", "Cash Flow"],
            "inputs": ["bank_id", "status"],
            "outputs": ["items"],
            "description": "Monitors active bank certificates, interest rates, posted interest, and maturity dates.",
        }]

    def get_data(self, user: Any, limit: int = 20) -> dict[str, Any]:
        from datetime import date, timedelta
        today = date.today()
        one_year_later = today + timedelta(days=365)

        active_certs = list(BankCertificate.objects.filter(status__iexact="active").select_related("bank"))
        
        tot_amount = sum(float(c.amount or 0) for c in active_certs)
        tot_monthly = sum(float(c.interest_value or 0) for c in active_certs)

        near_maturities = []
        for c in active_certs:
            if c.expiry_date and today <= c.expiry_date <= one_year_later:
                near_maturities.append({
                    "id": c.id,
                    "bank": c.bank.name if c.bank else "",
                    "amount": float(c.amount or 0),
                    "interest_rate": float(c.interest_rate or 0),
                    "issue_date": str(c.issue_date),
                    "expiry_date": str(c.expiry_date),
                    "days_to_maturity": (c.expiry_date - today).days,
                })

        certs = list(
            BankCertificate.objects.select_related("bank")
            .order_by("-amount")
            .values("id", "amount", "interest_rate", "interest_value", "issue_date", "expiry_date", "bank__name", "status")[:limit]
        )

        return {
            "summary": {
                "total_active_certificates_principal": tot_amount,
                "total_monthly_interest_income": tot_monthly,
                "active_certificates_count": len(active_certs),
                "maturing_near_future_count": len(near_maturities),
            },
            "near_maturities": near_maturities,
            "items": certs,
        }
