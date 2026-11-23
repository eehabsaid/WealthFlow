"""
Certificate interest + maturity events for the commitments calendar.

Taken from the same schedule CashFlowForecastService uses
(cash_flow_forecast_service.certificate_schedule), via the ForecastSeries, so
posted interest, the maturity-period interest and the base conversion can never
diverge from the forecast. `amount` stays in the certificate's own currency;
`amount_base` is the forecast's own conversion.
"""
from __future__ import annotations

from typing import List

from .event_shape import _in_range, _make


class CertificateEventsMixin:
    def _certificate_events(self) -> List[dict]:
        out: List[dict] = []
        for item in self.series.certificate_items(self.end):
            if not _in_range(self.start, self.end, item.event_date):
                continue
            cert = item.certificate
            maturity = item.event_type == "certificate_maturity"
            out.append(_make(
                item.event_date, "income", item.event_type, "actual",
                "commitments_event_" + item.event_type,
                amount=item.amount, amount_base=item.amount_base, currency_code=item.currency_code,
                source="BankCertificate", source_id=cert.id, bank_id=cert.bank_id, status="active",
                extra={"principal": round(item.principal, 2), "interest": round(item.interest, 2)} if maturity else None,
            ))
        return out
