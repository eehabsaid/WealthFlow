from django.urls import include, path
from . import views
from .views import ExportExcelWorkbookView

urlpatterns = [
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/signup/", views.signup_view, name="signup"),
    path("accounts/forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("accounts/reset-password/<str:token>/", views.reset_password_view, name="reset_password"),
    path("accounts/verify-email/<str:token>/", views.verify_email_view, name="verify_email"),
    path("accounts/pending-approval/", views.pending_approval_view, name="pending_approval"),
    path("accounts/account-rejected/", views.account_rejected_view, name="account_rejected"),
    path("accounts/account-disabled/", views.account_disabled_view, name="account_disabled"),
    path("accounts/admin-approve/<str:token>/", views.admin_approve_account_view, name="admin_approve_account"),
    path("accounts/admin-reject/<str:token>/", views.admin_reject_account_view, name="admin_reject_account"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("api/auth/login/", views.LoginAPIView.as_view()),
    path("api/auth/signup/", views.SignupAPIView.as_view()),
    path("api/auth/logout/", views.LogoutAPIView.as_view()),
    path("api/auth/forgot-password/", views.forgot_password_view),
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
    path("api/salary/generate-current/", views.GenerateCurrentSalaryView.as_view()),
    path("api/salary/", views.SalaryListView.as_view()),
    path("api/salary/<int:pk>/", views.SalaryDetailView.as_view()),
    path("api/salary/<int:pk>/mark-paid/", views.MarkSalaryPaidView.as_view()),
    path("api/per-diems/", views.PerDiemListView.as_view()),
    path("api/per-diems/<int:pk>/", views.PerDiemDetailView.as_view()),
    path("api/per-diems/currencies/", views.PerDiemCurrencyListView.as_view()),
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
    path("api/balance-transfers/", views.BalanceTransferListView.as_view()),
    path("api/balance-transfers/<int:pk>/", views.BalanceTransferDetailView.as_view()),
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
    path("api/settings/email-templates/", views.EmailTemplateListView.as_view()),
    path("api/settings/email-templates/<int:pk>/", views.EmailTemplateDetailView.as_view()),
    path("api/settings/email-test/", views.EmailSettingsTestView.as_view()),
    path("api/settings/gold-types/", views.GoldTypeSettingsListView.as_view()),
    path("api/settings/gold-types/<int:pk>/", views.GoldTypeSettingsDetailView.as_view()),
    path("api/settings/gold-purities/", views.GoldPuritySettingsListView.as_view()),
    path("api/settings/gold-purities/<int:pk>/", views.GoldPuritySettingsDetailView.as_view()),
    # Backup & Restore
    path("api/settings/backup/create/", views.BackupCreateView.as_view()),
    path("api/settings/backup/list/", views.BackupListView.as_view()),
    path("api/settings/backup/delete/", views.BackupDeleteView.as_view()),
    path("api/settings/backup/restore/", views.BackupRestoreView.as_view()),
    # Documentation Engine
    path("api/settings/documentation/capture/", views.CaptureScreenshotsView.as_view()),
    path("api/settings/documentation/generate-docs/", views.GenerateDocumentsView.as_view()),
    path("api/settings/documentation/validate-capture/", views.ValidateCaptureView.as_view()),
    path("api/settings/documentation/validate-generate/", views.ValidateGenerationView.as_view()),
    path("api/settings/documentation/cancel/", views.CancelDocumentationView.as_view()),
    path("api/settings/documentation/status/", views.DocumentationStatusView.as_view()),
    path("api/settings/documentation/devices/", views.DocumentationDevicesView.as_view()),
    path("api/settings/documentation/history/", views.DocumentationHistoryView.as_view()),
    path("api/settings/documentation/open/", views.OpenFolderView.as_view()),
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

    path(
        "api/asset-furniture/",
        views.AssetFurnitureListView.as_view(),
    ),
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
        "api/fixed-assets/<int:pk>/valuation/refresh/",
        views.FixedAssetValuationRefreshView.as_view(),
    ),
    path(
        "api/certificate-forecast/",
        views.CertificateForecastView.as_view(),
    ),
    path(
        "api/financial-advisor/cash-flow-forecast/",
        views.CashFlowForecastView.as_view(),
    ),
    path(
        "api/financial-advisor/wealth-growth-forecast/",
        views.WealthGrowthForecastView.as_view(),
    ),
    path(
        "api/financial-advisor/overview/",
        views.OverviewView.as_view(),
    ),
    path(
        "api/financial-advisor/portfolio-optimizer/",
        views.PortfolioOptimizerView.as_view(),
    ),
    path(
        "api/financial-advisor/risk-analysis/",
        views.RiskAnalysisView.as_view(),
    ),
    path(
        "api/financial-advisor/spending-intelligence/",
        views.SpendingIntelligenceView.as_view(),
    ),
    path(
        "api/financial-advisor/opportunity-detection/",
        views.OpportunityDetectionView.as_view(),
    ),
    path(
        "api/financial-advisor/performance/",
        views.PerformanceView.as_view(),
    ),
    path(
        "api/financial-advisor/what-if-simulator/",
        views.WhatIfSimulatorView.as_view(),
    ),
    path(
        "api/financial-advisor/scenario-planner/compare/",
        views.ScenarioComparisonView.as_view(),
    ),
    path(
        "api/scenarios/event-definitions/",
        views.ScenarioEventDefinitionsView.as_view(),
    ),
    path(
        "api/scenarios/",
        views.ScenarioListCreateView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/",
        views.ScenarioDetailView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/events/",
        views.ScenarioEventListCreateView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/events/<int:event_id>/",
        views.ScenarioEventDetailView.as_view(),
    ),
    path(
        "api/scenarios/<int:pk>/duplicate/",
        views.ScenarioDuplicateView.as_view(),
    ),
    path(
        "api/financial-advisor/goal-planning/",
        views.GoalPlanningView.as_view(),
    ),
    path("api/goals/", views.GoalListView.as_view()),
    path("api/goals/<int:pk>/", views.GoalDetailView.as_view()),
    path(
        "api/documents/categories/",
        views.DocumentCategoriesView.as_view(),
    ),
    path(
        "api/documents/file/<int:document_id>/",
        views.DocumentFileView.as_view(),
    ),
    path(
        "api/documents/<str:parent_type>/<int:parent_id>/",
        views.DocumentListUploadView.as_view(),
    ),
    path('api/', include('i18n_manager.urls')),
]
