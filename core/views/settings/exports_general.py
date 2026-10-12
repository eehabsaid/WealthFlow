# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false
"""General settings tabs: currencies, app settings, e-mail templates, backup, vendor assets, property rates, companies, banks, reminders, certificate statuses, translations, legal text, account retention.

Part of the umbrella in core/views/settings/__init__.py (split so no file passes ~200 lines)."""

from core.views.settings.currency_views import (
    CurrencyListView,
    CurrencyDetailView,
)
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
from core.views.settings.vendor_assets_views import VendorAssetsUpdateView
from core.views.settings.property_rate_views import ScrapePropertyRatesView
from core.views.settings.company_views import (
    CompanyListView,
    CompanyDetailView,
)
from core.views.settings.bank_views import (
    BankListView,
    BankDetailView,
    BankWithBalanceListView,
)
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
from core.views.settings.account_retention_views import AccountRetentionView
from core.views.settings.legal_text_views import (
    LegalConsentView,
    LegalTextDetailView,
    LegalTextListView,
)

__all__ = [
    "AccountRetentionView",
    "CurrencyListView",
    "CurrencyDetailView",
    "SettingsView",
    "EmailTemplateListView",
    "LegalConsentView",
    "LegalTextDetailView",
    "LegalTextListView",
    "EmailTemplateDetailView",
    "EmailSettingsTestView",
    "BackupCreateView",
    "BackupListView",
    "BackupDeleteView",
    "BackupRestoreView",
    "VendorAssetsUpdateView",
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
]
