"""
Unified permission-key namespace for the role-based access system.

Two families of grantable keys exist:
  - main-app pages (PAGE_PERMISSION_CHOICES, in core/constants/__init__.py)
  - settings tabs (SETTINGS_TAB_CHOICES, below)

A handful of settings tabs are intentionally NOT grantable via a role or a
per-user override, no matter how permissive the role — they require
`is_sysadmin` directly: Roles management itself (you can't delegate the
ability to hand out delegation), User Management (creates/deletes accounts,
flips is_sysadmin), and Billing Plans (which also hosts the Payment Gateway
/ Paymob key fields inline on the same tab).
"""

SETTINGS_TAB_CHOICES = [
    ("settings_languages", "Settings: Languages"),
    ("settings_companies", "Settings: Companies"),
    ("settings_banks", "Settings: Banks"),
    ("settings_currency", "Settings: Currency"),
    ("settings_users", "Settings: User Management"),
    ("settings_billing", "Settings: Billing Plans & Payment Gateway"),
    ("settings_emailtemplates", "Settings: Email Templates"),
    ("settings_translations", "Settings: Translations"),
    ("settings_translationcoverage", "Settings: Translation Coverage"),
    ("settings_reminders", "Settings: Reminders"),
    ("settings_certstatus", "Settings: Certificate Status"),
    ("settings_goldsettings", "Settings: Gold Settings"),
    ("settings_propertyvaluation", "Settings: Property Valuation"),
    ("settings_dashboard", "Settings: Dashboard"),
    ("settings_backuprestore", "Settings: Backup & Restore"),
    ("settings_documentation", "Settings: Documentation"),
    ("settings_aiadvisor", "Settings: AI Advisor"),
    ("settings_roles", "Settings: Roles"),
]

# Never grantable via Role or per-user override — always requires is_sysadmin.
SYSADMIN_ONLY_SETTINGS_TABS = ["settings_users", "settings_billing", "settings_roles"]

SETTINGS_TAB_KEYS = [key for key, _ in SETTINGS_TAB_CHOICES]

GRANTABLE_SETTINGS_TAB_CHOICES = [
    c for c in SETTINGS_TAB_CHOICES if c[0] not in SYSADMIN_ONLY_SETTINGS_TABS
]


def _grantable_page_choices():
    """Main-app page choices, minus the legacy `user_management` key (superseded
    by the sysadmin-only `settings_users` tab key above)."""
    from core.constants import PAGE_PERMISSION_CHOICES

    return [c for c in PAGE_PERMISSION_CHOICES if c[0] != "user_management"]


def grantable_permission_choices():
    """The full set of (key, label) pairs assignable to a Role or as a
    per-user override. Computed lazily to avoid a circular import with
    core/constants/__init__.py."""
    return _grantable_page_choices() + GRANTABLE_SETTINGS_TAB_CHOICES


def grantable_permission_keys():
    return [key for key, _ in grantable_permission_choices()]
