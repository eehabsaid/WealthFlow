"""Pure, deterministic aggregation helpers for ExpensesDataProvider. No I/O,
no Django imports beyond what the caller already resolved — easy to unit
test in isolation from the ORM.
"""

from __future__ import annotations


def build_category_breakdown(by_category: dict[str, float], total_spending_home: float, format_currency) -> dict:
    """ALL-TIME per-category totals + percentage of ALL-TIME total spending.
    NOT scoped to any month/year — see category_breakdown_note in provider.py
    for why that distinction matters."""
    breakdown = {}
    for cat_name, cat_val in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        pct = (round((cat_val / total_spending_home) * 100.0, 1)) if total_spending_home > 0 else 0.0
        breakdown[cat_name] = {
            "total_spending": round(cat_val, 2),
            "total_spending_formatted": format_currency(round(cat_val, 2)),
            "percentage": pct,
            "percentage_formatted": f"{pct:.1f}%",
        }
    return breakdown


def build_monthly_summary(by_month: dict[tuple[int, int], dict[str, float]], format_currency) -> list[dict]:
    """One entry per (year, month) with a TOTAL only (no category split) —
    see build_monthly_category_breakdown for the per-category version."""
    summary = []
    for (m_year, m_month) in sorted(by_month.keys(), reverse=True):
        bucket = by_month[(m_year, m_month)]
        summary.append({
            "year": m_year,
            "month": m_month,
            "total_spending": round(bucket["total"], 2),
            "total_spending_formatted": format_currency(round(bucket["total"], 2)),
            "transactions_count": int(bucket["count"]),
        })
    return summary


def build_monthly_category_breakdown(
    by_month_category: dict[tuple[int, int], dict[str, float]],
    by_month: dict[tuple[int, int], dict[str, float]],
    months_cap: int,
    format_currency,
) -> list[dict]:
    """Per-category totals WITHIN each (year, month) — the field that answers
    'detail/breakdown of expenses for <month>' questions. Without this,
    nothing deterministic in the payload can answer a month+category question:
    category_breakdown is all-time, monthly_summary has no category split, and
    the model was left to filter recent_expenses (a capped, unsorted-by-month
    subset) and sum it by hand — exactly the kind of multi-step arithmetic
    small local models get wrong (confirmed: reported figures for Sept 2026
    matched neither the correct per-category month totals nor any all-time
    figure, for a real account)."""
    result = []
    for (m_year, m_month) in sorted(by_month_category.keys(), reverse=True)[:months_cap]:
        cats = by_month_category[(m_year, m_month)]
        month_total = by_month[(m_year, m_month)]["total"]
        categories = {}
        for cat_name, cat_val in sorted(cats.items(), key=lambda x: x[1], reverse=True):
            pct = (round((cat_val / month_total) * 100.0, 1)) if month_total > 0 else 0.0
            categories[cat_name] = {
                "total_spending": round(cat_val, 2),
                "total_spending_formatted": format_currency(round(cat_val, 2)),
                "percentage_of_month": pct,
            }
        result.append({
            "year": m_year,
            "month": m_month,
            "total_spending_formatted": format_currency(round(month_total, 2)),
            "categories": categories,
        })
    return result
