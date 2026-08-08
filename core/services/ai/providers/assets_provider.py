"""
Fixed Assets & Gold Data Provider for AI business context. Read-only.
Enforces multi-tenant scoping, physical gold spot pricing (karat conversion), portfolio allocation, and home currency conversions.
"""

from __future__ import annotations

from typing import Any
from core.models import FixedAsset, GoldPrice
from core.services.ai.providers.base import BaseContextProvider


class FixedAssetsDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "fixed_assets"

    @property
    def name(self) -> str:
        return "Fixed Assets & Gold Portfolio"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Fixed Assets & Gold Portfolio",
            "provided_by": "FixedAssetsDataProvider",
            "consumes": ["FixedAsset", "GoldDetails", "GoldPrice"],
            "used_by": ["Financial Advisor", "Portfolio Allocator", "AI Advisor"],
            "inputs": ["user"],
            "outputs": ["summary", "items", "allocation_breakdown"],
            "description": "Calculates real estate, vehicle, physical gold karat spot valuations, total asset net worth, asset class allocation %, and pre-converted home currency metrics deterministically.",
        }]

    def get_data(self, user: Any, limit: int | None = None) -> dict[str, Any]:
        home_currency = self.get_user_primary_currency(user)

        # 1. Multi-tenant User Scoping
        qs = FixedAsset.objects.all()
        has_user_field = any(f.name == "user" for f in FixedAsset._meta.fields)
        if user and user.is_authenticated and has_user_field:
            qs = qs.filter(user=user)

        if limit is not None and limit > 0:
            qs = qs[:limit]

        assets_raw = list(qs)

        # 2. Fetch Latest Gold Spot Price for Karat Math
        latest_gold_price = GoldPrice.objects.order_by("-fetched_at").first()

        total_assets_val_home = 0.0
        allocation_by_class: dict[str, float] = {}
        items = []

        for asset in assets_raw:
            a_type = asset.asset_type or "Other Assets"

            # Check if asset has gold karat details for spot valuation
            current_val = float(asset.current_market_value or asset.purchase_price or 0)

            if a_type.lower() == "gold" and latest_gold_price and asset.gold_details:
                gd = asset.gold_details
                g_weight = float(gd.weight or 0)
                g_purity = str(gd.purity or "").lower()

                # Karat multiplier calculation
                if "24" in g_purity:
                    spot_g = float(latest_gold_price.carat_24k or 0)
                elif "22" in g_purity:
                    spot_g = float(latest_gold_price.carat_22k or 0)
                elif "18" in g_purity:
                    spot_g = float(latest_gold_price.carat_18k or 0)
                else:  # Default to 21K spot price
                    spot_g = float(latest_gold_price.carat_21k or 0)

                if spot_g > 0 and g_weight > 0:
                    current_val = g_weight * spot_g

            val_home = self.convert_to_home_currency(current_val, home_currency, home_currency)
            total_assets_val_home += val_home
            allocation_by_class[a_type] = allocation_by_class.get(a_type, 0.0) + val_home

            items.append({
                "id": asset.id,
                "name": asset.name,
                "asset_type": a_type,
                "status": asset.status,
                "purchase_price": float(asset.purchase_price or 0),
                "purchase_price_formatted": self.format_currency(float(asset.purchase_price or 0), home_currency),
                "current_market_value": current_val,
                "current_market_value_formatted": self.format_currency(current_val, home_currency),
                "valuation_source": asset.valuation_source,
                "notes": asset.notes or "",
            })

        # Calculate Asset Allocation Percentages
        allocation_breakdown = {}
        for a_class, a_val in allocation_by_class.items():
            pct = (round((a_val / total_assets_val_home) * 100.0, 1)) if total_assets_val_home > 0 else 0.0
            allocation_breakdown[a_class] = {
                "value": round(a_val, 2),
                "value_formatted": self.format_currency(round(a_val, 2), home_currency),
                "allocation_pct": pct,
                "allocation_pct_formatted": f"{pct:.1f}%",
            }

        return {
            "summary": {
                "total_fixed_assets_value": round(total_assets_val_home, 2),
                "total_fixed_assets_value_formatted": self.format_currency(round(total_assets_val_home, 2), home_currency),
                "total_assets_count": len(items),
                "home_currency": home_currency,
                "allocation_breakdown": allocation_breakdown,
            },
            "items": items,
        }
