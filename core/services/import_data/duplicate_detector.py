"""Flag import rows that likely already exist as an Expense, so the
confirm step can skip them instead of creating duplicates. A row is a
duplicate when an existing expense for the same owner has the same
date, the same amount (compared in the row's own currency-neutral
amount, not amount_base, since the import row hasn't been converted
yet), and a similar description.
"""
from decimal import Decimal

from core.models import Expense

AMOUNT_TOLERANCE = Decimal("0.01")


def find_duplicates(owner, parsed_rows):
    """parsed_rows: list of dicts with 'date' (date obj), 'amount' (float),
    'description' (str). Returns a set of indices into parsed_rows that
    match an existing Expense for this owner."""
    dates = {r["date"] for r in parsed_rows if r.get("date")}
    if not dates:
        return set()
    existing = list(
        Expense.objects.filter(owner=owner, date__in=dates).values("date", "amount", "description")
    )
    duplicate_indices = set()
    for idx, row in enumerate(parsed_rows):
        if not row.get("date"):
            continue
        row_amount = Decimal(str(row.get("amount") or 0))
        row_desc = (row.get("description") or "").strip().lower()
        for existing_row in existing:
            if existing_row["date"] != row["date"]:
                continue
            if abs(Decimal(str(existing_row["amount"])) - row_amount) > AMOUNT_TOLERANCE:
                continue
            if (existing_row["description"] or "").strip().lower() != row_desc:
                continue
            duplicate_indices.add(idx)
            break
    return duplicate_indices
