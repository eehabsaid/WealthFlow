"""Umbrella re-export for the Fixed Assets domain: fixed_asset_views.py
(list/detail, photos, documents, renovations, acquisition costs,
maintenance, insurance, furniture, valuation history, sale, USD rate)
plus asset_valuation_views.py (the valuation refresh action + its
salary-trigger-day helper).

Whenever fixed_asset_views.py or asset_valuation_views.py grow and
add/remove a public name, update the imports/__all__ below to match —
this file is what core/views/__init__.py depends on, so no other file
needs to change when those are reorganized internally.
"""

from .fixed_asset_views import (
    FixedAssetListView,
    FixedAssetDetailView,
    FixedAssetPhotoView,
    AssetPhotoView,
    DocumentListUploadView,
    DocumentFileView,
    DocumentCategoriesView,
    AssetRenovationListView,
    AssetRenovationDetailView,
    AssetRenovationCategoriesView,
    AssetAcquisitionCostListView,
    AssetAcquisitionCostDetailView,
    AssetAcquisitionCostCategoriesView,
    AssetMaintenanceListView,
    AssetMaintenanceDetailView,
    AssetInsuranceListView,
    AssetInsuranceDetailView,
    AssetFurnitureListView,
    AssetFurnitureDetailView,
    AssetFurnitureCategoriesView,
    AssetValuationHistoryListView,
    AssetValuationHistoryDetailView,
    AssetSaleView,
    FixedAssetUsdRateView,
)
from .asset_valuation_views import FixedAssetValuationRefreshView, _salary_trigger_day

__all__ = [
    "FixedAssetListView",
    "FixedAssetDetailView",
    "FixedAssetPhotoView",
    "AssetPhotoView",
    "DocumentListUploadView",
    "DocumentFileView",
    "DocumentCategoriesView",
    "AssetRenovationListView",
    "AssetRenovationDetailView",
    "AssetRenovationCategoriesView",
    "AssetAcquisitionCostListView",
    "AssetAcquisitionCostDetailView",
    "AssetAcquisitionCostCategoriesView",
    "AssetMaintenanceListView",
    "AssetMaintenanceDetailView",
    "AssetInsuranceListView",
    "AssetInsuranceDetailView",
    "AssetFurnitureListView",
    "AssetFurnitureDetailView",
    "AssetFurnitureCategoriesView",
    "AssetValuationHistoryListView",
    "AssetValuationHistoryDetailView",
    "AssetSaleView",
    "FixedAssetUsdRateView",
    "FixedAssetValuationRefreshView",
    "_salary_trigger_day",
]
