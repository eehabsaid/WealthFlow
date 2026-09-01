from .auth_views import AdminRequiredMixin
from .auth_views import LoginAPIView
from .auth_views import SignupAPIView
from .auth_views import LogoutAPIView
from .auth_views import CurrentUserView
from .settings import UserListView
from .settings import UserDetailView
from .settings import UserPermissionListView
from .settings import UserBulkActionView
from .settings import UserPermissionDetailView
from .settings import PagePermissionChoicesView
from .auth_views import UpdateProfileView
from .auth_views import login_view
from .auth_views import signup_view
from .auth_views import forgot_password_view
from .auth_views import reset_password_view
from .auth_views import verify_email_view
from .auth_views import pending_approval_view
from .auth_views import account_rejected_view
from .auth_views import account_disabled_view
from .auth_views import admin_approve_account_view
from .auth_views import admin_reject_account_view
from .auth_views import logout_view
from .settings import user_management_page
from .auth_views import create_user_profile
from .auth_views import _build_user_dict
from .auth_views import _get_user_allowed_pages
from .auth_views import _request_lang
from .auth_views import _render_auth
from .auth_views import _render_auth_status
from .settings import CompanyListView
from .settings import CompanyDetailView
from .salary_views import SalaryListView
from .salary_views import SalaryDetailView
from .salary_views import GenerateCurrentSalaryView
from .salary_views import MarkSalaryPaidView
from .salary_views import SalarySummaryView
from .salary_views import PerDiemListView
from .salary_views import PerDiemDetailView
from .salary_views import PerDiemCurrencyListView
from .settings import BankListView
from .settings import BankDetailView
from .settings import BankWithBalanceListView
from .certificate_views import BankCertificateListView
from .certificate_views import BankCertificateDetailView
from .certificate_views import BankCertificateInterestHistoryView
from .certificate_views import _run_certificate_interest_sync
from .balance import BalanceListView
from .balance import BalanceDetailView
from .expense_category_views import ExpenseCategoryListView
from .expense_category_views import ExpenseCategoryDetailView
from .expense_category_views import ExpenseSubcategoryListView
from .expense_category_views import ExpenseSubcategoryDetailView
from .expense_views import ExpenseListView
from .expense_views import ExpenseDetailView
from .expense_summary_views import ExpenseSummaryView
from .report_views import ExportExcelWorkbookView
from .report_views import export_excel
from .report_views import GenerateReportView
from .report_views import SalaryReportView
from .report_views import BalanceReportView
from .report_views import CertificateReportView
from .report_views import FixedAssetPdfReportView
from .report_views import FixedAssetExcelReportView
from core.reports.report_generators import format_arabic
from core.reports.report_generators import get_text
from core.reports.report_generators import _fixed_asset_report_queryset
from core.reports.report_generators import _fixed_asset_report_context
from core.reports.report_generators import _fixed_asset_display_value
from core.reports.report_generators import _fixed_asset_report_label
from core.reports.report_generators import _fixed_asset_user_text
from core.reports.report_generators import _fixed_asset_pdf_table
from core.reports.report_generators import _build_fixed_asset_pdf_story
from core.reports.report_generators import month_sort_key
from .dashboard_views import DashboardSummaryView
from .balance import CertificateForecastView
from .balance import CashFlowForecastView
from .balance import WealthGrowthForecastView
from .balance import PortfolioOptimizerView
from .balance import RiskAnalysisView
from .balance import SpendingIntelligenceView
from .balance import OpportunityDetectionView
from .balance import PerformanceView
from .balance import WhatIfSimulatorView
from .balance import OverviewView
from .balance import (
    ScenarioEventDefinitionsView,
    ScenarioListCreateView,
    ScenarioDetailView,
    ScenarioEventListCreateView,
    ScenarioEventDetailView,
    ScenarioComparisonView,
    ScenarioDuplicateView,
)
from .dashboard_views import index
from .dashboard_views import _api_auth_required
from .dashboard_views import _parse_iso_date
from .settings import SettingsView
from .settings import EmailTemplateListView
from .settings import EmailTemplateDetailView
from .settings import EmailSettingsTestView
from .settings import AISettingsView
from .settings import AIConnectionTestView
from .settings import AIProviderListView
from .settings import ScrapePropertyRatesView
from .settings import GoldTypeSettingsListView
from .settings import GoldTypeSettingsDetailView
from .settings import GoldPuritySettingsListView
from .settings import GoldPuritySettingsDetailView
from .settings import ExchangeRateListView
from .settings import ExchangeRateRefreshView
from .settings import GoldPriceListView
from .settings import GoldPriceRefreshView
from .settings import CurrencyListView
from .settings import CurrencyDetailView
from .settings import _seed_gold_settings_defaults
from .settings import (
    BackupCreateView,
    BackupListView,
    BackupDeleteView,
    BackupRestoreView,
)
from .goal_views import GoalPlanningView
from .goal_views import GoalListView
from .goal_views import GoalDetailView
from .fixed_asset_views import FixedAssetListView
from .fixed_asset_views import FixedAssetDetailView
from .fixed_asset_views import FixedAssetPhotoView
from .fixed_asset_views import AssetPhotoView
from .fixed_asset_views import DocumentListUploadView
from .fixed_asset_views import DocumentFileView
from .fixed_asset_views import DocumentCategoriesView
from .fixed_asset_views import AssetRenovationListView
from .fixed_asset_views import AssetRenovationDetailView
from .fixed_asset_views import AssetRenovationCategoriesView
from .fixed_asset_views import AssetAcquisitionCostListView
from .fixed_asset_views import AssetAcquisitionCostDetailView
from .fixed_asset_views import AssetAcquisitionCostCategoriesView
from .fixed_asset_views import AssetMaintenanceListView
from .fixed_asset_views import AssetMaintenanceDetailView
from .fixed_asset_views import AssetInsuranceListView
from .fixed_asset_views import AssetInsuranceDetailView
from .fixed_asset_views import AssetFurnitureListView
from .fixed_asset_views import AssetFurnitureDetailView
from .fixed_asset_views import AssetFurnitureCategoriesView
from .fixed_asset_views import AssetValuationHistoryListView
from .fixed_asset_views import AssetValuationHistoryDetailView
from .fixed_asset_views import AssetSaleView
from .fixed_asset_views import FixedAssetUsdRateView
from .expense_views import (
    User
)
from .balance import (
    BalanceTransferListView,
    BalanceTransferDetailView
)
from .balance import (
    BankInterestListView,
    BankInterestDetailView
)
from .balance import (
    CreditCardPaymentListView,
    CreditCardPaymentDetailView
)
from .balance import (
    CurrencyExchangeListView,
    CurrencyExchangeDetailView,
    CurrencyExchangeCalculateView,
    CurrencyExchangeFormOptionsView,
)
from .settings import ReminderRuleListView
from .settings import ReminderRuleDetailView
from .settings import ReminderCheckView
from .settings import ReminderLogListView
from .settings import CertificateStatusListView
from .settings import CertificateStatusDetailView
from .settings import get_translations
from .settings import save_translations
from .settings import scan_translations
from .asset_valuation_views import FixedAssetValuationRefreshView
from .asset_valuation_views import _salary_trigger_day


__all__ = [
    "AdminRequiredMixin",
    "LoginAPIView",
    "SignupAPIView",
    "LogoutAPIView",
    "CurrentUserView",
    "UserListView",
    "UserDetailView",
    "UserPermissionListView",
    "UserBulkActionView",
    "UserPermissionDetailView",
    "PagePermissionChoicesView",
    "UpdateProfileView",
    "login_view",
    "signup_view",
    "forgot_password_view",
    "reset_password_view",
    "verify_email_view",
    "pending_approval_view",
    "account_rejected_view",
    "account_disabled_view",
    "admin_approve_account_view",
    "admin_reject_account_view",
    "logout_view",
    "user_management_page",
    "create_user_profile",
    "_build_user_dict",
    "_get_user_allowed_pages",
    "_request_lang",
    "_render_auth",
    "_render_auth_status",
    "CompanyListView",
    "CompanyDetailView",
    "SalaryListView",
    "SalaryDetailView",
    "GenerateCurrentSalaryView",
    "MarkSalaryPaidView",
    "SalarySummaryView",
    "PerDiemListView",
    "PerDiemDetailView",
    "PerDiemCurrencyListView",
    "BankListView",
    "BankDetailView",
    "BankWithBalanceListView",
    "BankCertificateListView",
    "BankCertificateDetailView",
    "BankCertificateInterestHistoryView",
    "_run_certificate_interest_sync",
    "BalanceListView",
    "BalanceDetailView",
    "ExpenseCategoryListView",
    "ExpenseCategoryDetailView",
    "ExpenseSubcategoryListView",
    "ExpenseSubcategoryDetailView",
    "ExpenseListView",
    "ExpenseDetailView",
    "ExpenseSummaryView",
    "ExportExcelWorkbookView",
    "export_excel",
    "GenerateReportView",
    "SalaryReportView",
    "BalanceReportView",
    "CertificateReportView",
    "FixedAssetPdfReportView",
    "FixedAssetExcelReportView",
    "get_translations",
    "save_translations",
    "scan_translations",
    "format_arabic",
    "get_text",
    "_fixed_asset_report_queryset",
    "_fixed_asset_report_context",
    "_fixed_asset_display_value",
    "_fixed_asset_report_label",
    "_fixed_asset_user_text",
    "_fixed_asset_pdf_table",
    "_build_fixed_asset_pdf_story",
    "month_sort_key",
    "DashboardSummaryView",
    "CertificateForecastView",
    "CashFlowForecastView",
    "WealthGrowthForecastView",
    "PortfolioOptimizerView",
    "RiskAnalysisView",
    "SpendingIntelligenceView",
    "OpportunityDetectionView",
    "PerformanceView",
    "WhatIfSimulatorView",
    "OverviewView",
    "ScenarioEventDefinitionsView",
    "ScenarioListCreateView",
    "ScenarioDetailView",
    "ScenarioEventListCreateView",
    "ScenarioEventDetailView",
    "ScenarioComparisonView",
    "ScenarioDuplicateView",
    "index",
    "_api_auth_required",
    "_parse_iso_date",
    "SettingsView",
    "EmailTemplateListView",
    "EmailTemplateDetailView",
    "EmailSettingsTestView",
    "GoldTypeSettingsListView",
    "GoldTypeSettingsDetailView",
    "GoldPuritySettingsListView",
    "GoldPuritySettingsDetailView",
    "ExchangeRateListView",
    "ExchangeRateRefreshView",
    "GoldPriceListView",
    "GoldPriceRefreshView",
    "CurrencyListView",
    "CurrencyDetailView",
    "_seed_gold_settings_defaults",
    "BackupCreateView",
    "BackupListView",
    "BackupDeleteView",
    "BackupRestoreView",
    "GoalPlanningView",
    "GoalListView",
    "GoalDetailView",
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
    "User",
    "BalanceTransferListView",
    "BalanceTransferDetailView",
    "BankInterestListView",
    "BankInterestDetailView",
    "CreditCardPaymentListView",
    "CreditCardPaymentDetailView",
    "CurrencyExchangeListView",
    "CurrencyExchangeDetailView",
    "CurrencyExchangeCalculateView",
    "CurrencyExchangeFormOptionsView",
    "ReminderRuleListView",
    "ReminderRuleDetailView",
    "ReminderCheckView",
    "ReminderLogListView",
    "CertificateStatusListView",
    "CertificateStatusDetailView",
    "FixedAssetValuationRefreshView",
    "FixedAssetUsdRateView",
    "_salary_trigger_day",
    "DocumentationStatusView",
    "DocumentationDevicesView",
    "DocumentationHistoryView",
    "ValidateCaptureView",
    "ValidateGenerationView",
    "CaptureScreenshotsView",
    "GenerateDocumentsView",
    "CancelDocumentationView",
    "OpenFolderView",
    "AISettingsView",
    "AIConnectionTestView",
    "AIProviderListView",
    "ScrapePropertyRatesView",
    "AIChatView",
    "AIConversationListView",
    "AIConversationDetailView",
    "AIProgressView",
    "AIPlatformKnowledgeView",
    "AIPlatformDatasetView",
    "AIPlatformModelView",
    "AIPlatformBenchmarkView",
    "AIPromptListView",
    "AIPromptDetailView",
    "AIPromptFavoriteView",
    "AIPromptUseView",
    "AIPromptDuplicateView",
    "AIPromptCategoryListView",
    "AIPlatformKnowledgeDetailView",
]


from .ai_chat_views import AIChatView
from .ai_chat_views import AIConversationListView
from .ai_chat_views import AIConversationDetailView
from .ai_chat_views import AIProgressView

from .ai_platform_views import (
    AIPlatformKnowledgeView,
    AIPlatformDatasetView,
    AIPlatformModelView,
    AIPlatformBenchmarkView,
    AIPlatformKnowledgeDetailView,
)

from .ai_prompt_views import (
    AIPromptListView,
    AIPromptDetailView,
    AIPromptFavoriteView,
    AIPromptUseView,
    AIPromptDuplicateView,
    AIPromptCategoryListView,
)

from .settings import (
    DocumentationStatusView,
    DocumentationDevicesView,
    DocumentationHistoryView,
    ValidateCaptureView,
    ValidateGenerationView,
    CaptureScreenshotsView,
    GenerateDocumentsView,
    CancelDocumentationView,
    OpenFolderView,
)

