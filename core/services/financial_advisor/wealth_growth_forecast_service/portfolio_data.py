from __future__ import annotations

from datetime import date
from typing import Any, Dict

from core.models import BankCertificate, _is_certificate_active

from .utils import _to_float


class PortfolioDataMixin:
    """Gathers current portfolio state used as the baseline for forecasts."""

    def _portfolio(self) -> Dict[str, Any]:
        comp = self._net_worth_service.portfolio_components()
        forecast = self._net_worth_service.certificate_forecast_payload(today=self.today)
        cash_payload = self._cash_flow_service.payload()
        return {
            "current_net_worth": _to_float(comp["net_worth_egp"]),
            "current_cash": _to_float(cash_payload["checkpoints"]["current"]),
            "bank_balances": _to_float(comp["banks_total_egp"]),
            "fixed_assets": _to_float(comp["fixed_assets_total_egp"]),
            "gold_value": _to_float(comp["gold_value_egp"]),
            "certificate_value": _to_float(comp["certificate_total_egp"]),
            "certificate_interest_monthly": _to_float(comp["certificate_interest_total_egp"]),
            "cash_checkpoints": cash_payload["checkpoints"],
            "cash_timeline": cash_payload["timeline"],
            "gold_trend_30": _to_float(forecast["gold_trend_30"]),
            "gold_trend_90": _to_float(forecast["gold_trend_90"]),
            "gold_ma_gap_pct": _to_float(forecast["gold_ma_gap_pct"]),
            "gold_signal": _to_float(forecast["gold_signal"]),
            "monthly_rental_income": _to_float(forecast["monthly_rental_income"]),
            "monthly_salary": _to_float(forecast["monthly_salary"]),
            "monthly_certificate_income": _to_float(forecast["monthly_certificate_income"]),
            "total_monthly_income": _to_float(forecast["total_monthly_income"]),
        }

    def _get_active_certs(self):
        if not hasattr(self, "_cached_certs"):
            self._cached_certs = list(BankCertificate.objects.select_related("currency").all())
        return self._cached_certs

    def _active_certificate_principal_by_month(self, month_end: date) -> float:
        total = 0.0
        certs = self._get_active_certs()
        for cert in certs:
            if not _is_certificate_active(cert):
                continue
            if not cert.expiry_date:
                continue
            if cert.expiry_date <= month_end:
                continue
            total += _to_float(cert.amount) * self._convert_rate(cert.currency.code if cert.currency else "EGP")
        return total

    def _convert_rate(self, currency_code: str) -> float:
        rates = self._net_worth_service.portfolio_components()["rates"]
        code = str(currency_code or "EGP").upper()
        if code in ("", "EGP"):
            return 1.0
        return _to_float(rates.get(code)) or 0.0
