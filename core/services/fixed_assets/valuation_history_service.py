from __future__ import annotations

from django.utils import timezone

from core.models import AssetValuationHistory, FixedAsset


def record_valuation_history(
    asset: FixedAsset,
    market_value,
    source: str = "Automatic",
    valuation_date=None,
    notes: str = "",
) -> AssetValuationHistory:
    """Append a row to an asset's Valuation History tab.

    Used whenever a valuation is set by something other than the user
    typing a row into the Valuation History tab by hand — e.g. the
    "Refresh Valuation" button, or a scheduled provider sync. Always
    creates a new row (never updates an existing one), since this tab is
    a historical log of values over time, not a single current value.
    """
    return AssetValuationHistory.objects.create(
        asset=asset,
        valuation_date=valuation_date or timezone.localdate(),
        market_value=market_value,
        valuation_source=source,
        notes=notes,
    )
