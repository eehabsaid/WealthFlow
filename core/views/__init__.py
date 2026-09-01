"""Umbrella re-export for every view core/urls.py and other internal
callers reach via `from . import views` / `views.X`, so callers don't
need to know which domain file or subfolder a view actually lives in.

ORGANIZING PRINCIPLE: by functional domain, not by source file. Each
core/views/exports_*.py file owns re-exporting one domain's views from
wherever their logic actually lives (a flat file like auth_views.py,
or a subfolder like balance/ or settings/):
  - exports_auth.py            — login/signup/session + User & Permission mgmt
  - exports_financial_core.py  — Salary, Certificates, Goals, Dashboard, Company/Bank setup
  - exports_balance.py         — Balance, Forecasting & Scenario Planning (balance/ passthrough)
  - exports_expense_reports.py — Expenses + Excel/PDF report generation
  - exports_fixed_assets.py    — Fixed Assets (acquisition, renovation, insurance, etc.)
  - exports_ai_features.py     — AI Workspace: chat, platform panels, prompt library
  - exports_settings.py        — remaining Settings-page views (gold, market, backup, etc.)

STRUCTURE / CONVENTION — read this before adding or splitting a file:
  - This file stays a thin aggregator: import from the exports_*.py
    files below, never directly from a leaf view file. That keeps this
    file's line count independent of how many individual view files
    exist.
  - When a domain's logic view file(s) exceed ~200 lines, split them
    following the project's usual patterns (mixins, phase-functions,
    subfolders) — that's independent of this file, only the matching
    exports_*.py needs its imports/__all__ updated to match.
  - When a NEW domain is added, give it its own exports_<domain>.py
    file here rather than growing an existing one past ~150 names.
  - Always keep this file's own imports/__all__ up to date — this file
    is the single place `core/urls.py` and other internal callers
    depend on, so no call site needs to change when a domain's
    internals are reorganized.
"""

from .exports_auth import (
    AdminRequiredMixin, LoginAPIView, SignupAPIView, LogoutAPIView,
    CurrentUserView, UpdateProfileView, login_view, signup_view,
    forgot_password_view, reset_password_view, verify_email_view, pending_approval_view,
    account_rejected_view, account_disabled_view, admin_approve_account_view, admin_reject_account_view,
    logout_view, create_user_profile, _build_user_dict, _get_user_allowed_pages,
    _request_lang, _render_auth, _render_auth_status, UserListView,
    UserDetailView, UserPermissionListView, UserBulkActionView, UserPermissionDetailView,
    PagePermissionChoicesView, user_management_page,
)

from .exports_financial_core import (
    CompanyListView, CompanyDetailView, BankListView, BankDetailView,
    BankWithBalanceListView, SalaryListView, SalaryDetailView, GenerateCurrentSalaryView,
    MarkSalaryPaidView, SalarySummaryView, PerDiemListView, PerDiemDetailView,
    PerDiemCurrencyListView, BankCertificateListView, BankCertificateDetailView, BankCertificateInterestHistoryView,
    _run_certificate_interest_sync, GoalPlanningView, GoalListView, GoalDetailView,
    DashboardSummaryView, index, _api_auth_required, _parse_iso_date,
)

from .exports_balance import (
    BalanceListView, BalanceDetailView, CertificateForecastView, CashFlowForecastView,
    WealthGrowthForecastView, PortfolioOptimizerView, RiskAnalysisView, SpendingIntelligenceView,
    OpportunityDetectionView, PerformanceView, WhatIfSimulatorView, OverviewView,
    ScenarioEventDefinitionsView, ScenarioListCreateView, ScenarioDetailView, ScenarioEventListCreateView,
    ScenarioEventDetailView, ScenarioComparisonView, ScenarioDuplicateView, BalanceTransferListView,
    BalanceTransferDetailView, BankInterestListView, BankInterestDetailView, CardRenewalFeeListView,
    CardRenewalFeeDetailView, CreditCardPaymentListView,
    CreditCardPaymentDetailView, CurrencyExchangeListView, CurrencyExchangeDetailView, CurrencyExchangeCalculateView,
    CurrencyExchangeFormOptionsView,
)

from .exports_expense_reports import (
    ExpenseCategoryListView, ExpenseCategoryDetailView, ExpenseSubcategoryListView, ExpenseSubcategoryDetailView,
    ExpenseListView, ExpenseDetailView, User, ExpenseSummaryView,
    ExportExcelWorkbookView, export_excel, GenerateReportView, SalaryReportView,
    BalanceReportView, CertificateReportView, FixedAssetPdfReportView, FixedAssetExcelReportView,
    format_arabic, get_text, _fixed_asset_report_queryset, _fixed_asset_report_context,
    _fixed_asset_display_value, _fixed_asset_report_label, _fixed_asset_user_text, _fixed_asset_pdf_table,
    _build_fixed_asset_pdf_story, month_sort_key,
)

from .exports_fixed_assets import (
    FixedAssetListView, FixedAssetDetailView, FixedAssetPhotoView, AssetPhotoView,
    DocumentListUploadView, DocumentFileView, DocumentCategoriesView, AssetRenovationListView,
    AssetRenovationDetailView, AssetRenovationCategoriesView, AssetAcquisitionCostListView, AssetAcquisitionCostDetailView,
    AssetAcquisitionCostCategoriesView, AssetMaintenanceListView, AssetMaintenanceDetailView, AssetInsuranceListView,
    AssetInsuranceDetailView, AssetFurnitureListView, AssetFurnitureDetailView, AssetFurnitureCategoriesView,
    AssetValuationHistoryListView, AssetValuationHistoryDetailView, AssetSaleView, FixedAssetUsdRateView,
    FixedAssetValuationRefreshView, _salary_trigger_day,
)

from .exports_ai_features import (
    AIChatView, AIConversationListView, AIConversationDetailView, AIProgressView,
    AIPlatformKnowledgeView, AIPlatformDatasetView, AIPlatformModelView, AIPlatformBenchmarkView,
    AIPlatformKnowledgeDetailView, AIPromptListView, AIPromptDetailView, AIPromptFavoriteView,
    AIPromptUseView, AIPromptDuplicateView, AIPromptCategoryListView,
)

from .exports_settings import (
    SettingsView, EmailTemplateListView, EmailTemplateDetailView, EmailSettingsTestView,
    AISettingsView, AIConnectionTestView, AIProviderListView, ScrapePropertyRatesView,
    GoldTypeSettingsListView, GoldTypeSettingsDetailView, GoldPuritySettingsListView, GoldPuritySettingsDetailView,
    ExchangeRateListView, ExchangeRateRefreshView, GoldPriceListView, GoldPriceRefreshView,
    CurrencyListView, CurrencyDetailView, _seed_gold_settings_defaults, BackupCreateView,
    BackupListView, BackupDeleteView, BackupRestoreView, ReminderRuleListView,
    ReminderRuleDetailView, ReminderCheckView, ReminderLogListView, CertificateStatusListView,
    CertificateStatusDetailView, get_translations, save_translations, scan_translations,
    DocumentationStatusView, DocumentationDevicesView, DocumentationHistoryView, ValidateCaptureView,
    ValidateGenerationView, CaptureScreenshotsView, GenerateDocumentsView, CancelDocumentationView,
    OpenFolderView,
)

__all__ = [
    "AdminRequiredMixin", "LoginAPIView", "SignupAPIView", "LogoutAPIView", "CurrentUserView",
    "UpdateProfileView", "login_view", "signup_view", "forgot_password_view", "reset_password_view",
    "verify_email_view", "pending_approval_view", "account_rejected_view", "account_disabled_view", "admin_approve_account_view",
    "admin_reject_account_view", "logout_view", "create_user_profile", "_build_user_dict", "_get_user_allowed_pages",
    "_request_lang", "_render_auth", "_render_auth_status", "UserListView", "UserDetailView",
    "UserPermissionListView", "UserBulkActionView", "UserPermissionDetailView", "PagePermissionChoicesView", "user_management_page",
    "CompanyListView", "CompanyDetailView", "BankListView", "BankDetailView", "BankWithBalanceListView",
    "SalaryListView", "SalaryDetailView", "GenerateCurrentSalaryView", "MarkSalaryPaidView", "SalarySummaryView",
    "PerDiemListView", "PerDiemDetailView", "PerDiemCurrencyListView", "BankCertificateListView", "BankCertificateDetailView",
    "BankCertificateInterestHistoryView", "_run_certificate_interest_sync", "GoalPlanningView", "GoalListView", "GoalDetailView",
    "DashboardSummaryView", "index", "_api_auth_required", "_parse_iso_date", "BalanceListView",
    "BalanceDetailView", "CertificateForecastView", "CashFlowForecastView", "WealthGrowthForecastView", "PortfolioOptimizerView",
    "RiskAnalysisView", "SpendingIntelligenceView", "OpportunityDetectionView", "PerformanceView", "WhatIfSimulatorView",
    "OverviewView", "ScenarioEventDefinitionsView", "ScenarioListCreateView", "ScenarioDetailView", "ScenarioEventListCreateView",
    "ScenarioEventDetailView", "ScenarioComparisonView", "ScenarioDuplicateView", "BalanceTransferListView", "BalanceTransferDetailView",
    "BankInterestListView", "BankInterestDetailView", "CardRenewalFeeListView", "CardRenewalFeeDetailView", "CreditCardPaymentListView", "CreditCardPaymentDetailView", "CurrencyExchangeListView",
    "CurrencyExchangeDetailView", "CurrencyExchangeCalculateView", "CurrencyExchangeFormOptionsView", "ExpenseCategoryListView", "ExpenseCategoryDetailView",
    "ExpenseSubcategoryListView", "ExpenseSubcategoryDetailView", "ExpenseListView", "ExpenseDetailView", "User",
    "ExpenseSummaryView", "ExportExcelWorkbookView", "export_excel", "GenerateReportView", "SalaryReportView",
    "BalanceReportView", "CertificateReportView", "FixedAssetPdfReportView", "FixedAssetExcelReportView", "format_arabic",
    "get_text", "_fixed_asset_report_queryset", "_fixed_asset_report_context", "_fixed_asset_display_value", "_fixed_asset_report_label",
    "_fixed_asset_user_text", "_fixed_asset_pdf_table", "_build_fixed_asset_pdf_story", "month_sort_key", "FixedAssetListView",
    "FixedAssetDetailView", "FixedAssetPhotoView", "AssetPhotoView", "DocumentListUploadView", "DocumentFileView",
    "DocumentCategoriesView", "AssetRenovationListView", "AssetRenovationDetailView", "AssetRenovationCategoriesView", "AssetAcquisitionCostListView",
    "AssetAcquisitionCostDetailView", "AssetAcquisitionCostCategoriesView", "AssetMaintenanceListView", "AssetMaintenanceDetailView", "AssetInsuranceListView",
    "AssetInsuranceDetailView", "AssetFurnitureListView", "AssetFurnitureDetailView", "AssetFurnitureCategoriesView", "AssetValuationHistoryListView",
    "AssetValuationHistoryDetailView", "AssetSaleView", "FixedAssetUsdRateView", "FixedAssetValuationRefreshView", "_salary_trigger_day",
    "AIChatView", "AIConversationListView", "AIConversationDetailView", "AIProgressView", "AIPlatformKnowledgeView",
    "AIPlatformDatasetView", "AIPlatformModelView", "AIPlatformBenchmarkView", "AIPlatformKnowledgeDetailView", "AIPromptListView",
    "AIPromptDetailView", "AIPromptFavoriteView", "AIPromptUseView", "AIPromptDuplicateView", "AIPromptCategoryListView",
    "SettingsView", "EmailTemplateListView", "EmailTemplateDetailView", "EmailSettingsTestView", "AISettingsView",
    "AIConnectionTestView", "AIProviderListView", "ScrapePropertyRatesView", "GoldTypeSettingsListView", "GoldTypeSettingsDetailView",
    "GoldPuritySettingsListView", "GoldPuritySettingsDetailView", "ExchangeRateListView", "ExchangeRateRefreshView", "GoldPriceListView",
    "GoldPriceRefreshView", "CurrencyListView", "CurrencyDetailView", "_seed_gold_settings_defaults", "BackupCreateView",
    "BackupListView", "BackupDeleteView", "BackupRestoreView", "ReminderRuleListView", "ReminderRuleDetailView",
    "ReminderCheckView", "ReminderLogListView", "CertificateStatusListView", "CertificateStatusDetailView", "get_translations",
    "save_translations", "scan_translations", "DocumentationStatusView", "DocumentationDevicesView", "DocumentationHistoryView",
    "ValidateCaptureView", "ValidateGenerationView", "CaptureScreenshotsView", "GenerateDocumentsView", "CancelDocumentationView",
    "OpenFolderView",
]
