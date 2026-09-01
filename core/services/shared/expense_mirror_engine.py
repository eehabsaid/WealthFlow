"""Generic engine for keeping a read-only Expense mirror row in sync
with some other domain record (fixed-asset renovation/acquisition
cost/furniture, credit card payment, etc.), so spend accumulates in
Expenses/dashboards like a manual entry — without that domain ever
owning Expense CRUD directly.

Domain-specific callers (core/services/fixed_assets/,
core/services/balance/) each keep their own category/subcategory
naming and field mapping; this module only owns the shared
get-or-create-category + update-or-create-mirror mechanics.
"""

from datetime import date as _date
from decimal import Decimal

from django.utils.dateparse import parse_date

from core.models import Currency, Expense, ExpenseCategory, ExpenseSubcategory

# Expense.payment_method only offers Cash / Card / Bank Transfer / Other;
# some domain-side models additionally allow the distinct choice "Bank" —
# normalize it so the mirrored row renders with a value the Expenses UI
# actually recognizes.
_PAYMENT_METHOD_MAP = {
    "bank": "Bank Transfer",
}


def map_payment_method(value):
    raw = str(value or "Cash").strip()
    return _PAYMENT_METHOD_MAP.get(raw.lower(), raw or "Cash")


def normalize_date(value):
    """Some domain-side CRUD views assign a raw request string straight
    to a DateField without parsing, so the in-memory instance seen here
    can hold a str instead of a date — normalize defensively."""
    if isinstance(value, _date):
        return value
    if isinstance(value, str) and value:
        return parse_date(value)
    return None


def egp_currency():
    return Currency.objects.filter(code__iexact="EGP").order_by("id").first()


def get_or_create_mirror_subcategory(category_name, category_icon, category_color, subcategory_name):
    category, _ = ExpenseCategory.objects.get_or_create(
        name=category_name,
        defaults={"icon": category_icon, "color_hex": category_color},
    )
    subcategory, _ = ExpenseSubcategory.objects.get_or_create(
        category=category,
        name=subcategory_name,
    )
    return category, subcategory


def delete_mirror(source_type, source_id):
    if not source_id:
        return
    Expense.objects.filter(source_type=source_type, source_id=source_id).delete()


def sync_mirror(source_type, source_id, *, date_value, description, amount_egp, payment_method, bank_id, notes,
                 category, subcategory):
    """Create/update/delete the mirrored Expense row for one source
    record. A zero/blank amount deletes any existing mirror instead of
    leaving a noise $0 row (e.g. a draft the user hasn't filled in yet).
    """
    if not source_id:
        return None

    amount = Decimal(str(amount_egp or 0))
    if amount <= 0:
        delete_mirror(source_type, source_id)
        return None

    date_value = normalize_date(date_value) or _date.today()

    defaults = {
        "date": date_value,
        "year": date_value.year,
        "month": date_value.month,
        "category": category,
        "subcategory": subcategory,
        "description": (description or subcategory.name)[:300],
        "amount": amount,
        "exchange_rate": Decimal("1"),
        "amount_egp": amount,
        "currency": egp_currency(),
        "bank_id": bank_id,
        "payment_method": map_payment_method(payment_method),
        "notes": notes,
    }

    exp, _ = Expense.objects.update_or_create(
        source_type=source_type,
        source_id=source_id,
        defaults=defaults,
    )
    return exp
