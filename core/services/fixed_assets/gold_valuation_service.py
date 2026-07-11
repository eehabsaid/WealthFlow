from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from core.models import GoldPrice, GoldPriceHistory

@dataclass
class GoldPriceRefreshResult:
    saved: int = 0
    source_gold: str = "goldbullioneg.com"
    source_fx: str = "goldbullioneg.com"

    def to_dict(self):
        return {"saved": self.saved, "source_gold": self.source_gold, "source_fx": self.source_fx}

class GoldValuationService:
    def refresh_latest_prices(self):
        from core.integrations import fetch_latest_gold_prices

        res_data = fetch_latest_gold_prices()
        prices_egp = res_data["prices_egp"]
        usd_to_egp = res_data["usd_to_egp"]
        usd_per_oz = res_data["usd_per_oz"]

        usd_gram_24k = prices_egp[24]["sell"] / usd_to_egp if usd_to_egp else 0

        saved_price = {
            "carat_24k": round(prices_egp[24]["sell"], 2),
            "carat_22k": round(prices_egp[22]["sell"], 2),
            "carat_21k": round(prices_egp[21]["sell"], 2),
            "carat_18k": round(prices_egp[18]["sell"], 2),
            "carat_24k_buy": round(prices_egp[24]["buy"], 2),
            "carat_22k_buy": round(prices_egp[22]["buy"], 2),
            "carat_21k_buy": round(prices_egp[21]["buy"], 2),
            "carat_18k_buy": round(prices_egp[18]["buy"], 2),
            "usd_gram_24k": round(usd_gram_24k, 6),
            "usd_per_oz": round(usd_per_oz, 4),
            "usd_to_egp": round(usd_to_egp, 6),
            "source_gold": "goldbullioneg.com",
            "source_fx": "goldbullioneg.com",
        }

        with transaction.atomic():
            gp = GoldPrice.objects.create(**saved_price)
            GoldPriceHistory.objects.create(
                carat_24k=gp.carat_24k,
                carat_21k=gp.carat_21k,
                carat_18k=gp.carat_18k,
                usd_gram_24k=gp.usd_gram_24k,
                usd_per_oz=gp.usd_per_oz,
                usd_to_egp=gp.usd_to_egp,
            )

        from core.views import _refresh_all_gold_assets_from_live_prices

        _refresh_all_gold_assets_from_live_prices()

        return GoldPriceRefreshResult(saved=1)
