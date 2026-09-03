"""
fixed_assets package
=====================
Split from the former `fixed_assets.py` module (200-line refactor).

Sibling files:
- calculations_mixin.py   FixedAssetCalculationsMixin — related-object
                          lookups and derived financial metrics (ROI,
                          gain/loss, investment total, annual return).
- serialization_mixin.py  FixedAssetSerializationMixin — to_dict().
- model.py                 FixedAsset — the concrete Django model. Holds all
                          fields + Meta + save()/__str__, composing the
                          mixins above (Django requires fields to live on
                          the concrete model class).

Update this docstring whenever a sibling file is added, removed, or its
responsibility changes.
"""

from __future__ import annotations

from core.constants import ASSET_STATUS, ASSET_TYPES, VALUATION_SOURCE
from core.models.fixed_assets.model import FixedAsset

__all__ = ["FixedAsset", "ASSET_TYPES", "ASSET_STATUS", "VALUATION_SOURCE"]
