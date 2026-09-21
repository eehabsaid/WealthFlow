"""Per-user default (base) currency: the one place that answers 'which
currency is this user's primary currency?'. No other module may hardcode it.

Resolution order: the user's own choice (UserProfile.preferred_currency) ->
the platform default (AppSettings 'home_currency', editable by the sysadmin)
-> PLATFORM_FALLBACK_CURRENCY, the single last-resort constant.
"""
from django.conf import settings

from core.models import AppSettings, Currency, UserProfile

PLATFORM_FALLBACK_CURRENCY = "EGP"
# Catalog entries that are units, not money (see gold_sync_service): never a default currency.
NON_MONEY_CURRENCY_CODES = frozenset({"GOLD"})


def can_be_default(code) -> bool:
    return str(code or "").strip().upper() not in NON_MONEY_CURRENCY_CODES


def multi_currency_enabled() -> bool:
    return bool(getattr(settings, "MULTI_CURRENCY_ENABLED", False))


def platform_default_code() -> str:
    value = AppSettings.get("home_currency", PLATFORM_FALLBACK_CURRENCY)
    return str(value or PLATFORM_FALLBACK_CURRENCY).strip().upper()


def get_user_base_code(user) -> str:
    """Currency code every total/label for this user is expressed in."""
    if user is not None and getattr(user, "pk", None):
        chosen = UserProfile.objects.filter(user=user).values_list("preferred_currency", flat=True).first()
        if chosen and str(chosen).strip():
            return str(chosen).strip().upper()
    return platform_default_code()


def get_user_base_info(user) -> dict:
    code = get_user_base_code(user)
    currency = Currency.objects.filter(owner=user, code__iexact=code).first() if user else None
    return {
        "code": code,
        "symbol": (currency.symbol if currency and currency.symbol else code),
        "flag": currency.flag if currency else "",
        "name": currency.name if currency else code,
        "multi_currency_enabled": multi_currency_enabled(),
    }


def set_user_base_currency(user, code) -> str:
    """Validate and store the user's default currency. Raises ValueError with
    'invalid_currency' or 'multi_currency_disabled'."""
    code = str(code or "").strip().upper()
    if not can_be_default(code) or not Currency.objects.filter(owner=user, code__iexact=code).exists():
        raise ValueError("invalid_currency")
    if code != get_user_base_code(user) and not multi_currency_enabled():
        raise ValueError("multi_currency_disabled")
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.preferred_currency = code
    profile.save(update_fields=["preferred_currency"])
    return code
