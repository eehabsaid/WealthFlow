"""Pure helpers for CheckoutService (split out to keep both files under 200 lines).
CheckoutService re-exports every public name here, so existing import paths keep working."""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from core.services.billing.paymob_gateway import PaymobGateway

_MERCHANT_ORDER_PREFIX = "wf-inv-"
# ISO country for Paymob's billing_data, per charge currency (placeholder "NA" otherwise).
_COUNTRY_BY_CURRENCY = {"EGP": "EG", "SAR": "SA", "AED": "AE"}


def amount_to_cents(amount) -> int:
    """Smallest-unit amount Paymob expects, rounded (never truncated)."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class CheckoutError(Exception):
    pass


NO_GATEWAY_MESSAGE = (
    "Online payment isn't available yet. Please contact support to upgrade your plan."
)


def test_payments_allowed() -> bool:
    """Fake/test-mode payments need BOTH no real gateway AND the explicit
    BILLING_TEST_MODE setting (default = DEBUG). Production without Paymob
    therefore refuses checkout instead of handing out free upgrades."""
    return bool(getattr(settings, "BILLING_TEST_MODE", False)) and not PaymobGateway.any_configured()


def _billing_data_for(user, currency_code: str = "") -> dict:
    """Paymob requires a billing_data block; most fields aren't collected
    by WealthFlow, so placeholders are used where nothing real exists."""
    name = (getattr(user, "get_full_name", lambda: "")() or user.username or "Customer").strip()
    first, _, last = name.partition(" ")
    return {
        "first_name": first or "Customer",
        "last_name": last or "Customer",
        "email": getattr(user, "email", "") or "customer@example.com",
        "phone_number": "+00000000000",
        "apartment": "NA",
        "floor": "NA",
        "street": "NA",
        "building": "NA",
        "city": "NA",
        "country": _COUNTRY_BY_CURRENCY.get(str(currency_code).upper(), "NA"),
        "state": "NA",
    }
