# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""Umbrella re-export for every settings view, so core/views/__init__.py
can do `from .settings import X` without needing to know whether X lives
in a flat file here or in a per-domain subfolder (ai/, gold/, market/,
user/, documentation/).

ORGANIZING PRINCIPLE: by UI page, not by domain/resource. Every backend
view that only exists to back a tab on the Settings page lives somewhere
under core/views/settings/ — including views for models (Bank, Company,
User, CertificateStatus, ReminderRule) that are also used elsewhere in
the app. The one exception is a view that ISN'T tab-specific even though
it lives in a file that also has tab-specific views (e.g.
FixedAssetValuationRefreshView was split out to
core/views/asset_valuation_views.py because it's a Fixed Assets action,
not a Settings tab, even though it used to sit in the same file as the
Reminders tab views).

STRUCTURE / CONVENTION — read this before adding or splitting a file:
  - A single-resource view file (one Settings tab, e.g. currency_views.py)
    stays flat, directly in this settings/ folder.
  - The moment a domain needs MORE THAN ONE file (because a single file
    would exceed ~200 lines, or because it has natural sub-parts like
    views + helpers), give it its own subfolder here: settings/<domain>/,
    with an empty __init__.py inside it and its files split by concern
    (see settings/ai/, settings/gold/, settings/user/, or
    settings/documentation/ for the pattern).
  - Whenever ANY file in this package — flat or inside a subfolder —
    grows past ~200 lines, split it and, if that produces more than one
    file for that concern, move the results into (or create) a
    settings/<domain>/ subfolder following the same pattern.
  - Always update this __init__.py's imports/__all__ to match — this file
    is the single place core/views/__init__.py and core/urls.py depend
    on (both do `from . import views` / `from .settings import X`), so no
    other file needs to change when you reorganize inside settings/.
"""

from core.views.settings.currency_views import CurrencyListView, CurrencyDetailView
from core.views.settings.app_settings_views import SettingsView
from core.views.settings.email_template_views import (
    EmailTemplateListView,
    EmailTemplateDetailView,
    EmailSettingsTestView,
)
from core.views.settings.backup_views import (
    BackupCreateView,
    BackupListView,
    BackupDeleteView,
    BackupRestoreView,
)
from core.views.settings.property_rate_views import ScrapePropertyRatesView
from core.views.settings.company_views import CompanyListView, CompanyDetailView
from core.views.settings.bank_views import BankListView, BankDetailView, BankWithBalanceListView
from core.views.settings.reminder_views import (
    ReminderRuleListView,
    ReminderRuleDetailView,
    ReminderCheckView,
    ReminderLogListView,
)
from core.views.settings.cert_status_views import (
    CertificateStatusListView,
    CertificateStatusDetailView,
)
from core.views.settings.translation_views import (
    get_translations,
    save_translations,
    scan_translations,
)

from core.views.settings.gold.gold_settings_helpers import _seed_gold_settings_defaults
from core.views.settings.gold.gold_type_settings_views import (
    GoldTypeSettingsListView,
    GoldTypeSettingsDetailView,
)
from core.views.settings.gold.gold_purity_settings_views import (
    GoldPuritySettingsListView,
    GoldPuritySettingsDetailView,
)

from core.views.settings.market.exchange_rate_views import ExchangeRateListView, ExchangeRateRefreshView
from core.views.settings.market.gold_price_views import GoldPriceListView, GoldPriceRefreshView

from core.views.settings.ai.ai_settings_views import AISettingsView
from core.views.settings.ai.ai_connection_test_views import AIConnectionTestView
from core.views.settings.ai.ai_provider_views import AIProviderListView

from core.views.settings.user.user_views import (
    UserListView,
    UserDetailView,
    UserBulkActionView,
    user_management_page,
)
from core.views.settings.user.user_permission_views import (
    UserPermissionListView,
    UserPermissionDetailView,
    PagePermissionChoicesView,
)

from core.views.settings.documentation.documentation_core_views import (
    ValidateCaptureView,
    ValidateGenerationView,
    DocumentationDevicesView,
    DocumentationStatusView,
    DocumentationHistoryView,
    GenerateDocumentationView,
)
from core.views.settings.documentation.documentation_action_views import (
    CaptureScreenshotsView,
    GenerateDocumentsView,
    CancelDocumentationView,
    OpenFolderView,
)

__all__ = [
    "CurrencyListView",
    "CurrencyDetailView",
    "SettingsView",
    "EmailTemplateListView",
    "EmailTemplateDetailView",
    "EmailSettingsTestView",
    "BackupCreateView",
    "BackupListView",
    "BackupDeleteView",
    "BackupRestoreView",
    "ScrapePropertyRatesView",
    "CompanyListView",
    "CompanyDetailView",
    "BankListView",
    "BankDetailView",
    "BankWithBalanceListView",
    "ReminderRuleListView",
    "ReminderRuleDetailView",
    "ReminderCheckView",
    "ReminderLogListView",
    "CertificateStatusListView",
    "CertificateStatusDetailView",
    "get_translations",
    "save_translations",
    "scan_translations",
    "_seed_gold_settings_defaults",
    "GoldTypeSettingsListView",
    "GoldTypeSettingsDetailView",
    "GoldPuritySettingsListView",
    "GoldPuritySettingsDetailView",
    "ExchangeRateListView",
    "ExchangeRateRefreshView",
    "GoldPriceListView",
    "GoldPriceRefreshView",
    "AISettingsView",
    "AIConnectionTestView",
    "AIProviderListView",
    "UserListView",
    "UserDetailView",
    "UserBulkActionView",
    "user_management_page",
    "UserPermissionListView",
    "UserPermissionDetailView",
    "PagePermissionChoicesView",
    "ValidateCaptureView",
    "ValidateGenerationView",
    "DocumentationDevicesView",
    "DocumentationStatusView",
    "DocumentationHistoryView",
    "GenerateDocumentationView",
    "CaptureScreenshotsView",
    "GenerateDocumentsView",
    "CancelDocumentationView",
    "OpenFolderView",
]
