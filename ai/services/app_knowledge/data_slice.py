"""A tiny, owner-scoped slice of the user's own data for how/where/should questions (~300 chars).
Lets the model say "you already have an Other Assets item" instead of speaking in generalities.
Never counts as evidence for figures: it carries names and counts only."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)
MAX_CHARS = 450


def build_data_slice(user: Any) -> str:
    if user is None or not getattr(user, "is_authenticated", False):
        return ""
    try:
        from django.db.models import Count

        from core.models import Bank, ExpenseCategory, FixedAsset
        from core.services.shared.base_currency import get_user_base_code

        by_type = FixedAsset.objects.filter(owner=user, status="Owned").values_list("asset_type").annotate(n=Count("id")).order_by("asset_type")
        assets = ", ".join(f"{t} x{n}" for t, n in by_type) or "none"
        cats = ", ".join(ExpenseCategory.objects.filter(owner=user).order_by("order", "name").values_list("name", flat=True)[:10]) or "none"
        banks = Bank.objects.filter(owner=user).count()
        text = (f"User's own setup: base currency {get_user_base_code(user)}; owned assets by type: {assets}; "
                f"bank accounts: {banks}; expense categories: {cats}.")
        return text[:MAX_CHARS]
    except Exception as exc:  # the slice is optional context
        logger.info("data slice skipped: %s", exc)
        return ""
