from django.urls import include, path
from . import views
from .views import ExportExcelWorkbookView

urlpatterns = [
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/signup/", views.signup_view, name="signup"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("api/auth/login/", views.LoginAPIView.as_view()),
    path("api/auth/signup/", views.SignupAPIView.as_view()),
    path("api/auth/logout/", views.LogoutAPIView.as_view()),
    path("api/auth/me/", views.CurrentUserView.as_view()),
    path("api/auth/profile/", views.UpdateProfileView.as_view()),
    path("api/auth/profile/avatar/", views.UpdateProfileView.as_view()),
    path("api/users/", views.UserListView.as_view()),
    path("api/users/bulk/", views.UserBulkActionView.as_view()),
    path("api/users/<int:pk>/", views.UserDetailView.as_view()),
    path("api/users/<int:pk>/permissions/", views.UserPermissionListView.as_view()),
    path("api/users/permissions/<int:pk>/", views.UserPermissionDetailView.as_view()),
    path("api/users/permissions/pages/", views.PagePermissionChoicesView.as_view()),
    path("user-management/", views.user_management_page, name="user_management"),
    path("api/rates/", views.ExchangeRateListView.as_view()),
    path("api/rates/refresh/", views.ExchangeRateRefreshView.as_view()),
    path("api/gold/", views.GoldPriceListView.as_view()),
    path("api/gold/refresh/", views.GoldPriceRefreshView.as_view()),
    path("", views.index),
    path("api/companies/", views.CompanyListView.as_view()),
    path("api/companies/<int:pk>/", views.CompanyDetailView.as_view()),
    path("api/salary/summary/", views.SalarySummaryView.as_view()),
    path("api/salary/", views.SalaryListView.as_view()),
    path("api/salary/<int:pk>/", views.SalaryDetailView.as_view()),
    path("api/banks/", views.BankListView.as_view()),
    path("api/banks/<int:pk>/", views.BankDetailView.as_view()),
    path("api/bank-certificates/", views.BankCertificateListView.as_view()),
    path("api/bank-certificates/<int:pk>/", views.BankCertificateDetailView.as_view()),
    path(
        "api/bank-certificates/<int:certificate_id>/interest-history/",
        views.BankCertificateInterestHistoryView.as_view(),
    ),
    path("api/currencies/", views.CurrencyListView.as_view()),
    path("api/currencies/<int:pk>/", views.CurrencyDetailView.as_view()),
    path("api/balance/", views.BalanceListView.as_view()),
    path("api/balance/<int:pk>/", views.BalanceDetailView.as_view()),
    # Expenses
    path("api/expense-categories/", views.ExpenseCategoryListView.as_view()),
    path("api/expense-categories/<int:pk>/", views.ExpenseCategoryDetailView.as_view()),
    path("api/expense-subcategories/", views.ExpenseSubcategoryListView.as_view()),
    path(
        "api/expense-subcategories/<int:pk>/",
        views.ExpenseSubcategoryDetailView.as_view(),
    ),
    path("api/expenses/", views.ExpenseListView.as_view()),
    path("api/expenses/<int:pk>/", views.ExpenseDetailView.as_view()),
    path("api/expenses/summary/", views.ExpenseSummaryView.as_view()),
    # Reports
    path("api/reports/generate/", views.GenerateReportView.as_view()),
    path("api/settings/", views.SettingsView.as_view()),
    path("api/settings/gold-types/", views.GoldTypeSettingsListView.as_view()),
    path("api/settings/gold-types/<int:pk>/", views.GoldTypeSettingsDetailView.as_view()),
    path("api/settings/gold-purities/", views.GoldPuritySettingsListView.as_view()),
    path("api/settings/gold-purities/<int:pk>/", views.GoldPuritySettingsDetailView.as_view()),
    # excel export
    path("api/export/excel/", ExportExcelWorkbookView.as_view(), name="export_excel"),
    # ── Reminder Engine ──────────────────────────────────────────────────────
    path("api/reminders/", views.ReminderRuleListView.as_view()),
    path("api/reminders/<int:pk>/", views.ReminderRuleDetailView.as_view()),
    path("api/reminders/check/", views.ReminderCheckView.as_view()),
    path("api/reminders/log/", views.ReminderLogListView.as_view()),
    # ── Certificate Statuses ─────────────────────────────────────────────────
    path("api/cert-statuses/", views.CertificateStatusListView.as_view()),
    path("api/cert-statuses/<int:pk>/", views.CertificateStatusDetailView.as_view()),
    # ── Advanced Reports ─────────────────────────────────────────────────────
    path("api/reports/salary/", views.SalaryReportView.as_view()),
    path("api/reports/balance/", views.BalanceReportView.as_view()),
    path("api/reports/certificates/", views.CertificateReportView.as_view()),
    # ── Dashboard Summary ────────────────────────────────────────────────────
    path("api/dashboard/summary/", views.DashboardSummaryView.as_view()),
    # ── Fixed Assets ────────────────────────────────────────────────────────
    path("api/fixed-assets/", views.FixedAssetListView.as_view()),
    path("api/fixed-assets/<int:pk>/", views.FixedAssetDetailView.as_view()),
    path(
        "api/asset-renovations/",
        views.AssetRenovationListView.as_view(),
    ),
    path(
        "api/asset-renovations/<int:pk>/",
        views.AssetRenovationDetailView.as_view(),
    ),
    path(
        "api/asset-furniture/",
        views.AssetFurnitureListView.as_view(),
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
    path(
        "api/asset-insurance/",
        views.AssetInsuranceListView.as_view(),
    ),
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
        "api/certificate-forecast/",
        views.CertificateForecastView.as_view(),
    ),
    path('api/', include('i18n_manager.urls')),
]
