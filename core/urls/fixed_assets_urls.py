from django.urls import path
from .. import views

urlpatterns = [
    # ── Fixed Assets ────────────────────────────────────────────────────────
    path("api/fixed-assets/", views.FixedAssetListView.as_view()),
    path("api/fixed-assets/<int:pk>/", views.FixedAssetDetailView.as_view()),
    path("api/asset-renovations/", views.AssetRenovationListView.as_view()),
    path(
        "api/asset-renovations/categories/",
        views.AssetRenovationCategoriesView.as_view(),
    ),
    path(
        "api/asset-renovations/<int:pk>/",
        views.AssetRenovationDetailView.as_view(),
    ),
    path(
        "api/asset-acquisition-costs/",
        views.AssetAcquisitionCostListView.as_view(),
    ),
    path(
        "api/asset-acquisition-costs/categories/",
        views.AssetAcquisitionCostCategoriesView.as_view(),
    ),
    path(
        "api/asset-acquisition-costs/<int:pk>/",
        views.AssetAcquisitionCostDetailView.as_view(),
    ),
    path("api/asset-furniture/", views.AssetFurnitureListView.as_view()),
    path(
        "api/asset-furniture/categories/",
        views.AssetFurnitureCategoriesView.as_view(),
    ),
    path(
        "api/asset-furniture/<int:pk>/",
        views.AssetFurnitureDetailView.as_view(),
    ),
    path(
        "api/asset-valuations/",
        views.AssetValuationHistoryListView.as_view(),
    ),
    path(
        "api/asset-valuations/<int:pk>/",
        views.AssetValuationHistoryDetailView.as_view(),
    ),
    path(
        "api/asset-maintenance/",
        views.AssetMaintenanceListView.as_view(),
    ),
    path(
        "api/asset-maintenance/<int:pk>/",
        views.AssetMaintenanceDetailView.as_view(),
    ),
    path("api/asset-insurance/", views.AssetInsuranceListView.as_view()),
    path(
        "api/asset-insurance/<int:pk>/",
        views.AssetInsuranceDetailView.as_view(),
    ),
    path(
        "api/fixed-assets/<int:asset_id>/sale/",
        views.AssetSaleView.as_view(),
    ),
    path(
        "api/fixed-assets/<int:pk>/photos/",
        views.FixedAssetPhotoView.as_view(),
    ),
    path(
        "api/fixed-assets/<int:pk>/photos/<int:photo_id>/",
        views.FixedAssetPhotoView.as_view(),
    ),
    path(
        "api/fixed-assets/photo/<int:photo_id>/",
        views.AssetPhotoView.as_view(),
    ),
    path(
        "api/fixed-assets/reports/pdf/",
        views.FixedAssetPdfReportView.as_view(),
    ),
    path(
        "api/fixed-assets/reports/excel/",
        views.FixedAssetExcelReportView.as_view(),
    ),
    path(
        "api/fixed-assets/<int:pk>/valuation/refresh/",
        views.FixedAssetValuationRefreshView.as_view(),
    ),
    path(
        "api/fixed-assets/usd-rate/",
        views.FixedAssetUsdRateView.as_view(),
    ),
    path(
        "api/certificate-forecast/",
        views.CertificateForecastView.as_view(),
    ),
]
