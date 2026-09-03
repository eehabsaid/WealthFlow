"""
fixed_assets_realestate package
=================================
Split from the former `fixed_assets_realestate.py` module (200-line
refactor), following the flat one-model-per-file convention used by
`core/models/fixed_assets_history/`.

Sibling files:
- utils.py               _date_to_iso() shared date-formatting helper.
- real_estate_details.py RealEstateDetails model.
- asset_mortgage.py       AssetMortgage model + post_save/post_delete signals.
- asset_rental.py         AssetRental model + post_save/post_delete signals.

Update this docstring whenever a sibling file is added, removed, or its
responsibility changes.
"""

from __future__ import annotations

from core.models.fixed_assets_realestate.asset_mortgage import (
    AssetMortgage,
    handle_asset_mortgage_delete,
    handle_asset_mortgage_save,
)
from core.models.fixed_assets_realestate.asset_rental import (
    AssetRental,
    handle_asset_rental_delete,
    handle_asset_rental_save,
)
from core.models.fixed_assets_realestate.real_estate_details import RealEstateDetails

__all__ = [
    "RealEstateDetails",
    "AssetMortgage",
    "AssetRental",
    "handle_asset_mortgage_save",
    "handle_asset_mortgage_delete",
    "handle_asset_rental_save",
    "handle_asset_rental_delete",
]
