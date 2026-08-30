"""Bank/currency exposure and largest single balance entry.

NOTE (200-line file convention): part of the split of
core/services/financial_advisor/portfolio_optimizer_service.py (659 lines).
"""
from __future__ import annotations

from typing import List

from core.models import BalanceEntry, BankCertificate, _is_certificate_active

from .shared import _to_float


class ExposureMixin:
    def _bank_exposure(self, comp: dict) -> List[dict]:
        rates = comp.get("rates", {})
        bank_totals: dict = {}

        entries = BalanceEntry.objects.select_related("currency", "bank").all()
        for entry in entries:
            if not entry.bank_id:
                continue
            bank_name = entry.bank.name if entry.bank else "-"
            code = str(entry.currency.code if entry.currency else "EGP").upper()
            amount = _to_float(entry.amount)
            if code == "EGP":
                converted = amount
            elif code == "GOLD":
                converted = 0.0
            else:
                converted = amount * _to_float(rates.get(code))
            bank_totals[bank_name] = bank_totals.get(bank_name, 0.0) + converted

        for cert in BankCertificate.objects.select_related("bank", "currency").all():
            if not _is_certificate_active(cert):
                continue
            bank_name = cert.bank.name if cert.bank else "-"
            code = str(cert.currency.code if cert.currency else "EGP").upper()
            amount = _to_float(cert.amount)
            if code == "EGP":
                converted = amount
            else:
                converted = amount * _to_float(rates.get(code))
            bank_totals[bank_name] = bank_totals.get(bank_name, 0.0) + converted

        result = [
            {"bank_name": bank_name, "value": round(value, 2)}
            for bank_name, value in bank_totals.items()
            if value > 0
        ]
        result.sort(key=lambda item: item["value"], reverse=True)
        return result

    def _currency_exposure(self, comp: dict) -> List[dict]:
        rates = comp.get("rates", {})
        totals = comp.get("totals_by_currency", {})
        rows: List[dict] = []
        for code, amount in totals.items():
            upper_code = str(code or "").upper()
            value = _to_float(amount)
            if upper_code == "GOLD":
                value = _to_float(comp.get("gold_value_egp"))
            elif upper_code != "EGP":
                value = value * _to_float(rates.get(upper_code))
            rows.append({"code": upper_code or "EGP", "value": round(value, 2)})
        rows.sort(key=lambda item: item["value"], reverse=True)
        return rows

    def _largest_balance_entry(self, comp: dict) -> dict:
        rates = comp.get("rates", {})
        largest = {"title": "-", "value": 0.0}
        rows = BalanceEntry.objects.select_related("currency").all()
        for row in rows:
            code = str(row.currency.code if row.currency else "EGP").upper()
            amount = _to_float(row.amount)
            if code == "EGP":
                converted = amount
            elif code == "GOLD":
                continue
            else:
                converted = amount * _to_float(rates.get(code))
            if converted > largest["value"]:
                largest = {"title": row.title or "-", "value": round(converted, 2)}
        return largest
