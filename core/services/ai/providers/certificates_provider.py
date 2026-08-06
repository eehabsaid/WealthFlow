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
        certs = list(
            BankCertificate.objects.select_related("bank")
            .values("id", "amount", "interest_rate", "interest_value", "issue_date", "expiry_date", "bank__name", "status")[:limit]
        )
        return {"items": certs}
