from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.models import FixedAsset, AppSettings
from core.services.fixed_assets.valuation_history_service import record_valuation_history

from .base import PropertyValuationResult
from .configured_market_rate_provider import ConfiguredMarketRateProvider
from .external_api_provider import ExternalApiPropertyValuationProvider


class PropertyValuationService:
    """Abstracted property valuation pipeline.

    The first shipped provider is intentionally conservative: if a reliable estimate
    is not available, the service leaves the manual market value unchanged.
    """

    def __init__(self, providers=None):
        self.providers = providers or self._build_default_providers()

    def _build_default_providers(self):
        provider_map = {
            "external_api": ExternalApiPropertyValuationProvider(),
            "configured_market_rate": ConfiguredMarketRateProvider(),
        }

        order_raw = str(
            AppSettings.get(
                "property_valuation_provider_order",
                "external_api,configured_market_rate",
            )
            or ""
        )
        resolved = []
        for name in [item.strip().lower() for item in order_raw.split(",") if item.strip()]:
            provider = provider_map.get(name)
            if provider and provider not in resolved:
                resolved.append(provider)

        if not resolved:
            resolved.append(provider_map["configured_market_rate"])
        return resolved

    def refresh_asset(self, asset: FixedAsset, today=None):
        details = getattr(asset, "real_estate", None)
        if not details:
            return False, None

        for provider in self.providers:
            estimate = provider.estimate(asset, details)
            if estimate is None:
                continue
            self._store_estimate(asset, details, provider.name, estimate, today=today)
            return True, provider.name

        return False, None

    def refresh_all(self, today=None):
        result = PropertyValuationResult()
        assets = FixedAsset.objects.select_related("real_estate").filter(asset_type="Real Estate")
        with transaction.atomic():
            for asset in assets:
                result.processed_assets += 1
                updated, _ = self.refresh_asset(asset, today=today)
                if updated:
                    result.updated_assets += 1
                else:
                    result.skipped_assets += 1
        return result

    def _store_estimate(self, asset, details, provider_name, estimate, today=None):
        valuation_date = today or timezone.localdate()
        details.last_estimated_market_price = estimate
        details.last_valuation_date = valuation_date
        details.valuation_provider = provider_name
        details.save(update_fields=["last_estimated_market_price", "last_valuation_date", "valuation_provider", "updated_at"])
        asset.current_market_value = estimate
        asset.valuation_source = "Automatic"
        asset.last_valuation_date = valuation_date
        asset.save(update_fields=["current_market_value", "valuation_source", "last_valuation_date"])

        record_valuation_history(
            asset,
            market_value=estimate,
            source="Automatic",
            valuation_date=valuation_date,
            notes=f"Auto-synced via {provider_name}",
        )
