"""Market profile of a user, derived from their base currency (additive helper).

Egypt keeps its existing behavior untouched. A user whose base currency is a
Gulf currency (SAR, AED, ...) is a Gulf-market user: their currency catalog
has no EGP, their rates list hides EGP, and gold is priced from the
international spot price in their own currency instead of the Egyptian
dealer price.

No other module may hardcode the Gulf code list or the Gulf preset.
"""
from decimal import Decimal

from core.services.shared.base_currency import get_user_base_code

GULF_BASE_CODES = frozenset({"SAR", "AED", "KWD", "QAR", "BHD", "OMR"})

# Per-user catalog rows a Gulf-market user starts with (no EGP; EGP stays
# available through Settings > Currency for expats who send money home).
GULF_CURRENCY_PRESET = (
    {"code": "SAR", "symbol": "ر.س", "flag": "🇸🇦", "name": "Saudi Riyal"},
    {"code": "AED", "symbol": "د.إ", "flag": "🇦🇪", "name": "UAE Dirham"},
    {"code": "USD", "symbol": "$", "flag": "🇺🇸", "name": "US Dollar"},
    {"code": "EUR", "symbol": "€", "flag": "🇪🇺", "name": "Euro"},
    {"code": "Gold", "symbol": "g", "flag": "🪙", "name": "Gold (grams)"},
)

CARAT_PURITY = {"24k": Decimal("1"), "22k": Decimal(22) / 24, "21k": Decimal(21) / 24, "18k": Decimal(18) / 24}


def is_gulf_code(code) -> bool:
    return str(code or "").strip().upper() in GULF_BASE_CODES


def is_gulf_user(user) -> bool:
    return is_gulf_code(get_user_base_code(user))


def ensure_picker_currencies(user) -> None:
    """New users must be able to pick AED as base in the onboarding wizard.
    Additive and idempotent: only creates a missing AED row."""
    from core.models import Currency

    if Currency.objects.filter(owner=user, code__iexact="AED").exists():
        return
    aed = next(p for p in GULF_CURRENCY_PRESET if p["code"] == "AED")
    Currency.objects.create(owner=user, order=Currency.objects.filter(owner=user).count() + 1, **aed)


def ensure_gulf_catalog(user, base_code) -> None:
    """Create the missing Gulf preset currencies for `user`. Idempotent."""
    from core.models import Currency

    existing = {c.code.upper() for c in Currency.objects.filter(owner=user)}
    base = str(base_code).strip().upper()
    order = Currency.objects.filter(owner=user).count()
    wanted = [base] + [p["code"].upper() for p in GULF_CURRENCY_PRESET if p["code"].upper() != base]
    by_code = {p["code"].upper(): p for p in GULF_CURRENCY_PRESET}
    for code in wanted:
        if code in existing or code not in by_code:
            continue
        order += 1
        Currency.objects.create(owner=user, order=order, **by_code[code])


def _currency_is_referenced(currency) -> bool:
    """True if any row in any model points at this currency (balances,
    expenses, goals, assets...). Checked explicitly because several of those
    foreign keys are SET_NULL/CASCADE, which would silently alter user data."""
    from core.models import Currency

    for rel in Currency._meta.related_objects:
        if rel.related_model._base_manager.filter(**{rel.field.name: currency}).exists():
            return True
    return False


def prune_egp_for_gulf_user(user) -> None:
    """After a successful switch to a Gulf base: drop the EGP catalog row only
    when nothing references it. A used EGP row is always kept."""
    from core.models import Currency

    if not is_gulf_user(user):
        return
    egp = Currency.objects.filter(owner=user, code__iexact="EGP").first()
    if egp is not None and not _currency_is_referenced(egp):
        egp.delete()


def spot_gold_snapshot(user, latest_gold):
    """Gold price per gram per carat in the user's base currency, from the
    international spot (USD per gram of 24K). No dealer buy/sell spread."""
    from core.services.shared.currency_conversion_service import CurrencyConversionService

    base = get_user_base_code(user)
    usd_gram = Decimal(str(latest_gold.usd_gram_24k or 0))
    rate = CurrencyConversionService.calculate_exchange_rate("USD", base)
    prices = {f"carat_{k}": round(float(usd_gram * p * rate), 2) for k, p in CARAT_PURITY.items()}
    return {
        "currency": base,
        "market": "spot",
        "usd_to_base": float(rate),
        **prices,
        **{f"{k}_buy": v for k, v in prices.items()},
    }


def ensure_base_catalog(user, code) -> None:
    """Make sure `code` can be picked as base: Gulf codes get the Gulf preset;
    EGP (returning from a Gulf base) gets its catalog row back."""
    from core.models import Currency

    code = str(code or "").strip().upper()
    if is_gulf_code(code):
        ensure_gulf_catalog(user, code)
    elif code == "EGP" and not Currency.objects.filter(owner=user, code__iexact="EGP").exists():
        Currency.objects.create(
            owner=user, code="EGP", symbol="ج.م", flag="🇪🇬", name="Egyptian Pound",
            order=Currency.objects.filter(owner=user).count() + 1,
        )


def gold_price_for_user(user, latest_gold):
    """The latest gold row as the user's market sees it. Gulf-market users get
    an object whose carat_* / carat_*_buy fields are spot prices in their base
    currency (and `currency` is that code); everyone else gets `latest_gold`
    itself, untouched."""
    from types import SimpleNamespace

    if latest_gold is None or user is None or not is_gulf_user(user):
        return latest_gold
    snap = spot_gold_snapshot(user, latest_gold)
    return SimpleNamespace(
        fetched_at=latest_gold.fetched_at, usd_per_oz=latest_gold.usd_per_oz,
        usd_gram_24k=latest_gold.usd_gram_24k, usd_to_egp=latest_gold.usd_to_egp, **snap,
    )
