from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from core.models import ExchangeRate

@dataclass
class ExchangeRateRefreshResult:
    saved: int = 0
    source: str = "open.er-api.com"

    def to_dict(self):
        return {"saved": self.saved, "source": self.source}

class ExchangeRateService:
    CURRENCY_NAMES = {
        "USD": "US Dollar",
        "EUR": "Euro",
        "GBP": "Pound Sterling",
        "SAR": "Saudi Riyal",
        "AED": "UAE Dirham",
        "KWD": "Kuwaiti Dinar",
        "CAD": "Canadian Dollar",
        "CHF": "Swiss Franc",
        "JPY": "Japanese Yen",
        "CNY": "Chinese Yuan",
        "QAR": "Qatari Riyal",
        "BHD": "Bahraini Dinar",
        "OMR": "Omani Riyal",
        "JOD": "Jordanian Dinar",
        "NOK": "Norwegian Krone",
        "SEK": "Swedish Krona",
        "DKK": "Danish Krone",
        "AUD": "Australian Dollar",
    }

    def refresh_latest_rates(self):
        from core.integrations import fetch_latest_exchange_rates
        from core.services.exchange_rate_history_service import ExchangeRateHistoryService

        rates_raw = fetch_latest_exchange_rates()

        # ── Archive current rates BEFORE overwriting ───────────────────────────
        # Placed outside the transaction below so that an archive failure
        # (silently swallowed inside ExchangeRateHistoryService) can never
        # roll back the refresh of core_exchangerate.
        ExchangeRateHistoryService().archive_current_rates()
        # ──────────────────────────────────────────────────────────────────────

        saved = 0

        with transaction.atomic():
            ExchangeRate.objects.all().delete()
            for code, name in self.CURRENCY_NAMES.items():
                if code not in rates_raw:
                    continue
                egp_per_unit = 1.0 / float(rates_raw[code]) if float(rates_raw[code]) else 0
                spread = egp_per_unit * 0.005
                ExchangeRate.objects.create(
                    currency_code=code,
                    currency_name=name,
                    buy_rate=round(egp_per_unit - spread, 6),
                    sell_rate=round(egp_per_unit + spread, 6),
                    mid_rate=round(egp_per_unit, 6),
                    source="open.er-api.com",
                )
                saved += 1

        return ExchangeRateRefreshResult(saved=saved)
