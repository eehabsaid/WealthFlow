"""Who may read/write which AppSettings key through /api/settings/.

Layers, from most to least open:
  - USER_SCOPED_SETTING_KEYS (user_scoped_settings.py) + active_language:
    every logged-in user, their own value only.
  - MEMBER_READABLE_SETTING_KEYS: platform-global keys any logged-in user may
    read (never write) because the shell UI needs them.
  - GLOBAL_KEY_PERMISSIONS: a global key belongs to the Settings tab whose
    permission key is listed; holders of that permission may read/write it.
  - Everything else is sysadmin-only.

Secret keys (see SECRET_KEY_MARKERS) are never returned, not even to a
sysadmin: the API returns "<key>_is_set" ("true"/"false") instead.
"""

MEMBER_READABLE_SETTING_KEYS = frozenset({"available_languages"})

GLOBAL_KEY_PERMISSIONS = (
    ("smtp_", "settings_emailtemplates"),
    ("sender_email", "settings_emailtemplates"),
    ("administrator_notification_email", "settings_emailtemplates"),
    ("email_console_fallback", "settings_emailtemplates"),
    ("available_languages", "settings_languages"),
    ("ai_", "settings_aiadvisor"),
    ("paymob_", "settings_billing"),
    ("property_tax_", "settings_propertyvaluation"),
    ("home_currency", "settings_currency"),
)

SECRET_KEY_MARKERS = ("password", "api_key", "secret", "token")
