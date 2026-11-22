"""Regional constants, key helpers and the config error for Paymob."""

from __future__ import annotations




PAYMOB_BASE_URL = "https://accept.paymob.com/api"

# Paymob accounts are regional (Egypt, KSA, UAE ... each has its own host,
# credentials, integration and iframe). The default credentials (Settings >
# Billing Plans) serve the currencies listed in AppSettings
# "paymob_default_currencies" (default: EGP). A currency with its own regional
# account stores it under paymob_cfg_<CODE>_<field>; those win over the default.
DEFAULT_CURRENCIES_FALLBACK = "EGP"
_REGION_FIELDS = ("api_key", "hmac_secret", "integration_id", "iframe_id", "base_url")
_REGION_SECRET_FIELDS = ("api_key", "hmac_secret")


def region_key(code: str, field: str) -> str:
    return f"paymob_cfg_{str(code).strip().upper()}_{field}"


def normalize_base_url(value: str) -> str:
    """Accepts 'ksa.paymob.com', 'https://ksa.paymob.com' or '.../api'; returns
    the https .../api base. Empty input means the default Egypt host."""
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return PAYMOB_BASE_URL
    if not raw.startswith("https://"):
        raw = "https://" + raw.split("://", 1)[-1]
    if not raw.endswith("/api"):
        raw += "/api"
    return raw

# Exact, alphabetically-ordered field list Paymob's webhook HMAC is
# computed over for "TRANSACTION" callbacks, per Paymob's documented
# HMAC calculation for the transaction processed callback.
_HMAC_FIELDS = (
    "amount_cents",
    "created_at",
    "currency",
    "error_occured",
    "has_parent_transaction",
    "id",
    "integration_id",
    "is_3d_secure",
    "is_auth",
    "is_capture",
    "is_refunded",
    "is_standalone_payment",
    "is_voided",
    "order.id",
    "owner",
    "pending",
    "source_data.pan",
    "source_data.sub_type",
    "source_data.type",
    "success",
)


class PaymobConfigError(Exception):
    """Raised when a Paymob call is attempted without full configuration."""
