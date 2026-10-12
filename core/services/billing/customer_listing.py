"""Sysadmin customer listing: paginated users and lazily loaded invoices (fixed number of queries per page).

The old list loaded every user and issued ~3 queries per user (subscription, invoices, invoice count). A page now costs
a constant 5 queries (users, count, subscriptions, invoices via a window function, invoice counts) however many
customers exist, and each customer carries only its newest invoices; the rest are fetched on demand.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber

from core.models import Invoice, Subscription

User = get_user_model()

DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE = 25, 100
DEFAULT_INVOICE_LIMIT, MAX_INVOICE_LIMIT = 10, 50


def clamp_int(value, default: int, lo: int, hi: int) -> int:
    """`value` as an int within [lo, hi]; `default` when it is missing or not a number."""
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _row(user, sub, invoices, invoice_count) -> dict:
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "subscription": sub.to_dict() if sub else None,
        "invoices": [i.to_dict() for i in invoices],
        "invoice_count": invoice_count,
    }


def _newest_invoices(user_ids, limit: int) -> dict:
    """{owner_id: [newest `limit` invoices]} in one query (same order as Invoice.Meta: newest first)."""
    ranked = (
        Invoice.objects.filter(owner_id__in=user_ids)
        .annotate(rn=Window(RowNumber(), partition_by=F("owner_id"), order_by=[F("issued_at").desc(), F("id").desc()]))
        .filter(rn__lte=limit)
        .select_related("plan", "currency")
        .order_by("owner_id", "rn")
    )
    grouped = {uid: [] for uid in user_ids}
    for invoice in ranked:
        grouped[invoice.owner_id].append(invoice)
    return grouped


def customers_for(users, *, invoice_limit: int = DEFAULT_INVOICE_LIMIT) -> list:
    """Customer dicts for `users` (a list), batching subscription, invoice and count lookups."""
    ids = [u.id for u in users]
    subs = {s.owner_id: s for s in Subscription.objects.filter(owner_id__in=ids).select_related("plan")}
    counts = dict(Invoice.objects.filter(owner_id__in=ids).values_list("owner_id").annotate(n=Count("id")))
    invoices = _newest_invoices(ids, invoice_limit)
    return [_row(u, subs.get(u.id), invoices[u.id], counts.get(u.id, 0)) for u in users]


def customer_dict(user, *, invoice_limit: int = DEFAULT_INVOICE_LIMIT) -> dict:
    return customers_for([user], invoice_limit=invoice_limit)[0]


def list_customers(search: str = "", page=1, page_size=DEFAULT_PAGE_SIZE) -> dict:
    """One page of non-superuser customers: {customers, total, page, page_size, has_more}."""
    page_size = clamp_int(page_size, DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    qs = User.objects.filter(is_superuser=False)
    if search:
        qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search))
    qs = qs.order_by("username", "id")
    total = qs.count()
    page = clamp_int(page, 1, 1, max(1, -(-total // page_size)))
    start = (page - 1) * page_size
    users = list(qs[start : start + page_size])
    return {
        "customers": customers_for(users),
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": start + len(users) < total,
    }


def invoices_page(user, offset=0, limit=DEFAULT_INVOICE_LIMIT) -> dict:
    """A slice of one customer's invoices (newest first) for the lazily loaded 'Show more' in the invoices modal."""
    limit = clamp_int(limit, DEFAULT_INVOICE_LIMIT, 1, MAX_INVOICE_LIMIT)
    offset = clamp_int(offset, 0, 0, 10**9)
    qs = Invoice.objects.filter(owner=user).select_related("plan", "currency")
    total = qs.count()
    rows = list(qs[offset : offset + limit])
    return {"invoices": [i.to_dict() for i in rows], "total": total, "offset": offset, "has_more": offset + len(rows) < total}
