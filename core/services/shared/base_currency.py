"""Per-user default (base) currency: the one place that answers 'which
currency is this user's primary currency?'. No other module may hardcode it.

Resolution order: the user's own choice (UserProfile.preferred_currency) ->
the platform default (AppSettings 'home_currency', editable by the sysadmin)
-> PLATFORM_FALLBACK_CURRENCY, the single last-resort constant.
"""
from typing import Dict

from django.conf import settings
from django.db import transaction

from core.models import AppSettings, Currency, ExchangeRate, UserProfile
from core.services.shared.currency_conversion_service import RATE_PIVOT

PLATFORM_FALLBACK_CURRENCY = "EGP"
# Currency the stored gold prices are quoted in (the current source is Egyptian).
# Becomes a Gold Settings field in the gold delivery.
GOLD_PRICE_CURRENCY = "EGP"
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
        "pivot_currency": RATE_PIVOT,
        "name": currency.name if currency else code,
        "multi_currency_enabled": multi_currency_enabled(),
    }


def base_rates(user) -> Dict[str, float]:
    """code -> value of one unit of that currency in the user's default currency."""
    from core.services.shared.currency_conversion_service import CurrencyConversionService

    rates = CurrencyConversionService.get_rates_to_base(get_user_base_code(user))
    return {code: float(rate) for code, rate in rates.items()}


def pin_user_base_currency(user) -> str:
    """Save the resolved default on the profile so a later change of the
    platform default can never silently move an existing user's currency."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if not str(profile.preferred_currency or "").strip():
        profile.preferred_currency = platform_default_code()
        profile.save(update_fields=["preferred_currency"])
    return str(profile.preferred_currency).strip().upper()


def _has_market_rate(code: str) -> bool:
    from core.services.shared.currency_conversion_service import RATE_PIVOT

    return code == RATE_PIVOT or ExchangeRate.objects.filter(currency_code__iexact=code).exists()


def set_user_base_currency(user, code) -> str:
    """Validate and store the user's default currency. Raises ValueError with
    'invalid_currency', 'multi_currency_disabled', 'no_rate_for_currency' or
    'exchange_rate_missing' (a stored amount cannot be recalculated)."""
    code = str(code or "").strip().upper()
    if not can_be_default(code) or not Currency.objects.filter(owner=user, code__iexact=code).exists():
        raise ValueError("invalid_currency")
    if code != get_user_base_code(user):
        if not multi_currency_enabled():
            raise ValueError("multi_currency_disabled")
        if not _has_market_rate(code):
            raise ValueError("no_rate_for_currency")
    old_code = get_user_base_code(user)
    with transaction.atomic():
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.preferred_currency = code
        profile.save(update_fields=["preferred_currency"])
        if old_code != code:
            from core.services.shared.base_currency_recalc import recalculate_base_amounts

            recalculate_base_amounts(user, old_code, code)  # may raise; rolls back
    return code
