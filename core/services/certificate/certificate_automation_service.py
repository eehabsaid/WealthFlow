from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from core.models import BankCertificate, CertificateStatus

@dataclass
class CertificateAutomationResult:
    processed_certificates: int = 0
    closed_certificates: int = 0
    closed_ids: list[int] = field(default_factory=lambda: list[int]())

    def to_dict(self) -> dict[str, object]:
        return {
            "processed_certificates": self.processed_certificates,
            "closed_certificates": self.closed_certificates,
            "closed_ids": self.closed_ids,
        }

class CertificateAutomationService:
    def close_matured_certificates(self, today: Optional[date] = None) -> CertificateAutomationResult:
        current_date = today or timezone.localdate()
        result = CertificateAutomationResult()
        closed_name = self._closed_status_name()

        with transaction.atomic():
            certificates = list(
                BankCertificate.objects.select_for_update()
                .select_related("bank", "currency")
                .filter(expiry_date__lte=current_date)
            )

            for certificate in certificates:
                result.processed_certificates += 1
                if self._is_closed(certificate):
                    continue
                if not self._is_active(certificate):
                    continue
                certificate.status = closed_name
                certificate.save(update_fields=["status", "updated_at"])
                result.closed_certificates += 1
                certificate_pk: Any = getattr(certificate, "pk", None)
                if certificate_pk is not None:
                    result.closed_ids.append(int(certificate_pk))

        return result

    def _is_active(self, certificate: BankCertificate) -> bool:
        return str(certificate.status or "").strip().lower() == "active"

    def _is_closed(self, certificate: BankCertificate) -> bool:
        return str(certificate.status or "").strip().lower() == "closed"

    def _closed_status_name(self) -> str:
        closed_status = CertificateStatus.objects.filter(name__iexact="closed").order_by("order", "name").first()
        if closed_status:
            return closed_status.name
        return "Closed"
