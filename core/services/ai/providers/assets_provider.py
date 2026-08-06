"""
Fixed Assets Data Provider for AI business context. Read-only.
"""

from __future__ import annotations

from typing import Any
from django.db.models import Sum, Count
from core.models import FixedAsset
from core.services.ai.providers.base import BaseContextProvider


class FixedAssetsDataProvider(BaseContextProvider):
    @property
    def key(self) -> str:
        return "fixed_assets"

    @property
    def name(self) -> str:
        return "Fixed Assets (Real Estate, Vehicles, Gold, Other)"

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [{
            "name": "Fixed Asset Valuation & Asset Class Breakdown",
            "provided_by": "FixedAssetsDataProvider",
            "consumes": ["FixedAsset", "RealEstateDetails", "VehicleDetails", "GoldDetails"],
            "used_by": ["Portfolio", "Wealth Growth", "NetWorthService"],
            "inputs": ["asset_type", "status"],
            "outputs": ["by_type", "items"],
            "description": "Calculates valuation breakdown across real estate, vehicles, gold, and other fixed holdings.",
        }]

    def get_data(self, user: Any, limit: int = 20) -> dict[str, Any]:
        assets_by_type = list(
            FixedAsset.objects.values("asset_type")
            .annotate(total_value=Sum("purchase_price"), count=Count("id"))
            .order_by("-total_value")
        )
        asset_list = list(
            FixedAsset.objects.values("id", "name", "asset_type", "purchase_price", "status", "current_market_value")[:limit]
        )
        return {
            "by_type": assets_by_type,
            "items": asset_list,
        }
