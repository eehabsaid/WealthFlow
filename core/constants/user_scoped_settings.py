"""Which AppSettings keys read/written through the generic /api/settings/
endpoint are per-user vs platform-global.

To move a setting from global to per-user (or back), just add/remove its
key here — no other code changes needed. Everything NOT listed here stays
platform-global (e.g. SMTP config, available_languages — anything tied to
shared infrastructure or to files that physically exist once per
deployment)."""

USER_SCOPED_SETTING_KEYS = frozenset(
    {
        # Property Valuation tab
        "property_valuation_rate_map",
        "property_valuation_provider_order",
        "property_valuation_external_enabled",
        "property_valuation_external_url",
        "property_valuation_external_result_path",
        "property_valuation_external_timeout_secs",
        "property_valuation_external_headers",
        # Dashboard tab
        "dashboard_show_certs",
        "dashboard_show_reminders",
        "dashboard_show_salary",
        # Reminders tab
        "reminder_check_enabled",
        "cert_expiry_warning_days",
    }
)

# active_language is a special case: it's user-scoped via UserProfile
# .preferred_language (an existing dedicated field) rather than via a
# per-user AppSettings row — see app_settings_views.py.
ACTIVE_LANGUAGE_KEY = "active_language"
