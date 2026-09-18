# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false
"""
Gold asset pricing and balance synchronization.

Split into a package (200-line rule):
  - helpers.py : decimal/unit/purity conversion helpers
  - sync.py    : asset pricing refresh + balance sync business logic
  - __init__.py (this file) : umbrella re-export, preserving the exact
    (underscore-prefixed) import surface consumers already depend on —
    gold_valuation_service.py and several fixed_assets views import
    these "private" names directly.
"""

from core.services.fixed_assets.gold_sync_service.helpers import (
    _to_decimal,
    _gold_unit_factor,
    _gold_weight_in_grams,
    _normalize_gold_purity,
    _gold_sell_price_per_gram,
    _gold_cashback_per_gram,
    _latest_gold_price,
)
from core.services.fixed_assets.gold_sync_service.sync import (
    _refresh_gold_asset_pricing,
    _sync_gold_balance_from_assets,
    _refresh_all_gold_assets_from_live_prices,
    _sync_gold_details,
)

__all__ = [
    "_to_decimal",
    "_gold_unit_factor",
    "_gold_weight_in_grams",
    "_normalize_gold_purity",
    "_gold_sell_price_per_gram",
    "_gold_cashback_per_gram",
    "_latest_gold_price",
    "_refresh_gold_asset_pricing",
    "_sync_gold_balance_from_assets",
    "_refresh_all_gold_assets_from_live_prices",
    "_sync_gold_details",
]
