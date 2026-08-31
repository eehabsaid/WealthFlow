"""Umbrella re-export for the fixed asset "history" models, so
core/models/__init__.py can keep doing
`from .fixed_assets_history import X` without knowing these models live
in individual files here.

NOTE: Split out of the former core/models/fixed_assets_history.py (562
lines) per the 200-line file split rule.

STRUCTURE / CONVENTION — read this before adding or splitting a file:
  - One model per file, flat in this package (renovation.py, furniture.py,
    valuation_history.py, purchase_payment.py, sale.py,
    acquisition_cost.py). Each file also carries that model's own
    post_save/post_delete/pre_save signal receivers, since they're tightly
    coupled to the model they mutate.
  - If any single model file grows past ~200 lines (e.g. a model gains a
    large block of business-logic methods), split that file further and
    give it its own subfolder here: fixed_assets_history/<model>/.
  - All cross-file imports use absolute paths
    (`from core.models.fixed_assets import FixedAsset`), never relative
    imports.
"""
from .renovation import AssetRenovation  # noqa: F401 (import registers @receiver handlers)
from .furniture import AssetFurniture  # noqa: F401 (import registers @receiver handlers)
from .valuation_history import AssetValuationHistory
from .purchase_payment import AssetPurchasePayment
from .sale import (
    AssetSale,
    handle_asset_sale_pre_save,
    handle_asset_sale_save,
    handle_asset_sale_delete,
)
from .acquisition_cost import AssetAcquisitionCost  # noqa: F401 (import registers @receiver handlers)

__all__ = [
    "AssetRenovation",
    "AssetFurniture",
    "AssetValuationHistory",
    "AssetPurchasePayment",
    "AssetSale",
    "AssetAcquisitionCost",
    # re-exported so backup_serializer can disconnect/reconnect them by
    # name during restore (see reconnect_signals in backup_serializer.py)
    "handle_asset_sale_pre_save",
    "handle_asset_sale_save",
    "handle_asset_sale_delete",
]
