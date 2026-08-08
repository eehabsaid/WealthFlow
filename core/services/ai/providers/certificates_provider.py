"""
Bank Certificates Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, yield calculations, maturity dates, and home currency conversions.
"""

from __future__ import annotations

from typing import Any
from datetime import date
from core.models import BankCertificate
from core.services.ai.providers.base import BaseContextProvider


class BankCertificatesDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "bank_certificates"

    @property
    def name(self) -> str:
        return "Bank Certificates & Fixed Deposits"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Bank Certificates & Fixed Deposits",
            "provided_by": "BankCertificatesDataProvider",
            "consumes": ["BankCertificate", "Bank", "Currency"],
            "used_by": ["Financial Advisor", "Cash Flow Forecast", "AI Advisor"],
            "inputs": ["user"],
            "outputs": ["summary", "items"],
            "description": "Calculates active certificates principal, monthly interest payouts, weighted interest yield %, maturity countdowns, and currency conversions deterministically.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        home_currency = self.get_user_primary_currency(user)

        # 1. Multi-tenant User Scoping
        qs = BankCertificate.objects.all()
        has_user_field = any(f.name == "user" for f in BankCertificate._meta.fields)
        if user and user.is_authenticated and has_user_field:
            qs = qs.filter(user=user)

        active_qs = qs.filter(status__iexact="active").select_related("bank", "currency")
        if limit is not None and limit > 0:
            active_qs = active_qs[:limit]

        certs_raw = list(active_qs)

        total_principal_home = 0.0
        total_monthly_interest_home = 0.0
        weighted_rate_sum = 0.0
        items = []
        today = date.today()

        for cert in certs_raw:
            c_code = cert.currency.code if cert.currency else home_currency
            principal = float(cert.amount or 0)
            interest_val = float(cert.interest_value or 0)
            rate_pct = float(cert.interest_rate or 0)

            principal_home = self.convert_to_home_currency(principal, c_code, home_currency)
            interest_home = self.convert_to_home_currency(interest_val, c_code, home_currency)

            total_principal_home += principal_home
            total_monthly_interest_home += interest_home
            weighted_rate_sum += rate_pct * principal_home

            days_to_maturity = None
            if cert.expiry_date:
                days_to_maturity = (cert.expiry_date - today).days

            items.append({
                "id": cert.id,
                "bank_name": cert.bank.name if cert.bank else "",
                "amount": principal,
                "currency": c_code,
                "amount_formatted": self.format_currency(principal, c_code),
                "amount_in_home_currency": principal_home,
                "amount_in_home_currency_formatted": self.format_currency(principal_home, home_currency),
                "interest_rate": rate_pct,
                "interest_rate_formatted": f"{rate_pct:.2f}%",
                "interest_value_monthly": interest_val,
                "interest_value_monthly_formatted": self.format_currency(interest_val, c_code),
                "issue_date": cert.issue_date.isoformat() if cert.issue_date else "",
                "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else "",
                "days_to_maturity": days_to_maturity,
                "status": cert.status,
            })

        avg_weighted_rate = (
            round(weighted_rate_sum / total_principal_home, 2)
            if total_principal_home > 0 else 0.0
        )

        return {
            "summary": {
                "total_active_certificates_principal": round(total_principal_home, 2),
                "total_active_certificates_principal_formatted": self.format_currency(round(total_principal_home, 2), home_currency),
                "total_monthly_interest_income": round(total_monthly_interest_home, 2),
                "total_monthly_interest_income_formatted": self.format_currency(round(total_monthly_interest_home, 2), home_currency),
                "average_weighted_interest_rate_pct": avg_weighted_rate,
                "active_certificates_count": len(items),
                "home_currency": home_currency,
            },
            "items": items,
        }
