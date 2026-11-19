# Server-side search + filtering for the Expenses list endpoint.
# Kept out of the view so it can be unit-tested without HTTP.
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils.dateparse import parse_date


def _to_int(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _to_date(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return parse_date(str(value).strip())
    except ValueError:
        return None


def _to_decimal(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not d.is_finite():
        return None
    return d


def apply_expense_filters(qs, params):
    """Filter an Expense queryset by the list-view GET params.

    Invalid/missing values are ignored (treated as not provided) so a bad
    param can never raise. All filters combine with AND; search spans
    description, notes, category, subcategory, bank and payment method.
    """
    year = _to_int(params.get("year"))
    month = _to_int(params.get("month"))
    cat_id = _to_int(params.get("category"))
    sub_id = _to_int(params.get("subcategory"))
    bank_id = _to_int(params.get("bank"))
    pm = (params.get("payment_method") or "").strip()
    start = _to_date(params.get("start"))
    end = _to_date(params.get("end"))
    amount_min = _to_decimal(params.get("amount_min"))
    amount_max = _to_decimal(params.get("amount_max"))
    search = (params.get("search") or "").strip()

    if start and end:
        qs = qs.filter(date__gte=start, date__lte=end)
    else:
        if year:
            qs = qs.filter(year=year)
        if month:
            qs = qs.filter(month=month)

    if cat_id:
        qs = qs.filter(category_id=cat_id)
    if sub_id:
        # Validate the subcategory belongs to the selected category: a stale or
        # mismatched subcategory is ignored, never raised on.
        if cat_id:
            qs = qs.filter(subcategory__category_id=cat_id)
        qs = qs.filter(subcategory_id=sub_id)
    if bank_id:
        qs = qs.filter(bank_id=bank_id)
    if pm:
        qs = qs.filter(payment_method=pm)
    if amount_min is not None:
        qs = qs.filter(amount_base__gte=amount_min)
    if amount_max is not None:
        qs = qs.filter(amount_base__lte=amount_max)

    if search:
        qs = (
            qs.filter(
                Q(description__icontains=search)
                | Q(notes__icontains=search)
                | Q(category__name__icontains=search)
                | Q(subcategory__name__icontains=search)
                | Q(bank__name__icontains=search)
                | Q(payment_method__icontains=search)
            )
            .distinct()
        )

    return qs
