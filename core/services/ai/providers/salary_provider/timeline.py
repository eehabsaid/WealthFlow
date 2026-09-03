"""
Chronological entry analysis, the AI-facing capped monthly timeline, and the
single most-recent salary entry for the salary data provider.
"""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from core.services.ai.providers.salary_provider.constants import (
    MAX_TIMELINE_ENTRIES_FOR_AI,
    month_sort_key,
)


def load_entries_chronological(qs: QuerySet) -> list:
    """All entries, earliest -> latest."""
    all_entries_asc = list(qs.select_related("company").all())
    all_entries_asc.sort(key=month_sort_key)
    return all_entries_asc


def compute_career_growth(all_entries_asc: list, total_count: int) -> dict[str, Any]:
    first_historical_paid = None
    latest_historical_paid = None
    paid_consistent_count = 0

    for entry in all_entries_asc:
        p_val = float(entry.paid or 0)
        e_val = float(entry.expected or 0)
        if first_historical_paid is None and p_val > 0:
            first_historical_paid = p_val
        if p_val > 0:
            latest_historical_paid = p_val
            if p_val >= e_val:
                paid_consistent_count += 1

    career_overall_growth_pct = None
    if first_historical_paid and first_historical_paid > 0 and latest_historical_paid is not None:
        career_overall_growth_pct = round(
            ((latest_historical_paid - first_historical_paid) / first_historical_paid) * 100.0, 2
        )

    paid_consistency_pct = (
        round((paid_consistent_count / total_count) * 100.0, 1)
        if total_count > 0 else 100.0
    )

    return {
        "career_overall_growth_pct": career_overall_growth_pct,
        "paid_consistency_pct": paid_consistency_pct,
    }


def build_recent_monthly_timeline(
    all_entries_asc: list, limit: int | None, currency_code: str, format_currency
) -> list[dict[str, Any]]:
    """Timeline entry assembly (chronological, oldest -> newest)."""
    all_entries_desc = list(all_entries_asc)
    all_entries_desc.reverse()

    if limit is not None and limit > 0:
        timeline_entries = all_entries_desc[:limit]
    else:
        timeline_entries = all_entries_desc[:MAX_TIMELINE_ENTRIES_FOR_AI]
    timeline_entries.sort(key=month_sort_key)

    recent_monthly_timeline = []
    for entry in timeline_entries:
        p_val = float(entry.paid or 0)
        e_val = float(entry.expected or 0)
        b_val = float(entry.bonus or 0)
        recent_monthly_timeline.append({
            "year": entry.year,
            "month": entry.month,
            "company": entry.company.name if entry.company else "",
            "paid": p_val,
            "paid_formatted": format_currency(p_val, currency_code),
            "expected": e_val,
            "expected_formatted": format_currency(e_val, currency_code),
            "bonus": b_val,
            "bonus_formatted": format_currency(b_val, currency_code),
            "remaining": entry.remaining,
            "remaining_formatted": format_currency(entry.remaining, currency_code),
            "currency": currency_code,
            "notes": entry.notes or "",
        })
    return recent_monthly_timeline


def build_latest_salary_entry(all_entries_asc: list, currency_code: str, format_currency) -> dict[str, Any] | None:
    """
    The single most recent salary entry (by year+month), as an unambiguous
    standalone object — NOT an aggregate. This is the correct field to answer
    "what is the latest paid salary" — do not use yearly_summary/company_breakdown
    (those are SUMS across many entries) or scan recent_monthly_timeline for this.
    """
    if not all_entries_asc:
        return None
    latest_entry_obj = all_entries_asc[-1]
    return {
        "year": latest_entry_obj.year,
        "month": latest_entry_obj.month,
        "company": latest_entry_obj.company.name if latest_entry_obj.company else "",
        "paid": float(latest_entry_obj.paid or 0),
        "paid_formatted": format_currency(float(latest_entry_obj.paid or 0), currency_code),
        "expected": float(latest_entry_obj.expected or 0),
        "expected_formatted": format_currency(float(latest_entry_obj.expected or 0), currency_code),
        "bonus": float(latest_entry_obj.bonus or 0),
        "bonus_formatted": format_currency(float(latest_entry_obj.bonus or 0), currency_code),
    }
