"""Income Analytics service: one read-only build() for the API and both exports."""
from core.models import SalaryEntry
from core.services.reports.income_analytics import periods
from core.services.reports.income_analytics.sources import SOURCES, SOURCE_IDS, extract_all


def build_income_analytics(owner, query):
    """query: a django QueryDict (or any .get()-able) with mode/year/months/ya/yb/ma/mya/mb/myb/sources/basis."""
    basis = query.get("basis") if query.get("basis") in ("net", "gross") else "net"
    all_rows = extract_all(owner, basis)

    sources_param = periods.parse_sources(query.get("sources"))
    src_filter = set(sources_param) if sources_param else set(SOURCE_IDS)
    rows = [r for r in all_rows if r["source"] in src_filter]

    mode, periods_list = periods.resolve_periods(rows, query)
    months = periods.parse_months(query.get("months")) if mode != "mom" else []

    in_a = [r for r in all_rows if periods.in_period(r, periods_list[0], months)]
    in_b = [r for r in all_rows if periods.in_period(r, periods_list[1], months)] if len(periods_list) > 1 else []
    rows_a = [r for r in in_a if r["source"] in src_filter]
    rows_b = [r for r in in_b if r["source"] in src_filter]

    stats_a = periods.period_stats(rows_a)
    stats_b = periods.period_stats(rows_b) if rows_b is not None else None

    # off mode: previous period = the same months of the previous year
    prev_total = None
    if mode == "off":
        prev_year = periods_list[0]["year"] - 1
        prev_rows = [r for r in rows if r["year"] == prev_year and (not months or r["month"] in months)]
        prev_total = round(sum(r["amount"] for r in prev_rows), 2)

    groups = periods.group_rows(rows_a, rows_b, mode)
    comparing = len(periods_list) > 1

    records = []
    for pk, p_rows in (("A", rows_a), ("B", rows_b)):
        for r in p_rows:
            records.append({
                "source": r["source"],
                "key": periods.item_key(r, mode),
                "period": pk,
                "date": r["date"],
                "ref": r["ref"],
                "amount": r["amount"],
            })

    years_available = sorted({r["year"] for r in all_rows}, reverse=True)
    month_pairs = sorted({(r["year"], r["month"]) for r in all_rows}, reverse=True)
    latest_two_months = [
        {"year": y, "month": m} for y, m in month_pairs[:2]
    ]

    salary_gross_missing = basis == "gross" and SalaryEntry.objects.filter(
        company__owner=owner, gross__isnull=True
    ).exists()
    gross_used = basis == "gross"

    return {
        "mode": mode,
        "basis": basis,
        "gross_used": gross_used,
        "salary_gross_missing": salary_gross_missing,
        "years_available": years_available,
        "latest_two_months": latest_two_months,
        "sources": [
            {
                "id": s["id"],
                "color": s["color"],
                "total": round(sum(r["amount"] for r in in_a if r["source"] == s["id"]), 2),
                "count_a": sum(1 for r in in_a if r["source"] == s["id"]),
                "count_b": sum(1 for r in in_b if r["source"] == s["id"]),
            }
            for s in SOURCES
        ],
        "periods": [
            {
                "key": p["key"],
                "year": p["year"],
                "month": p["month"],
                "total": stats_a["total"] if p["key"] == "A" else stats_b["total"],
                "records": stats_a["records"] if p["key"] == "A" else stats_b["records"],
                "by_month": stats_a["by_month"] if p["key"] == "A" else stats_b["by_month"],
            }
            for p in periods_list
        ],
        "stats_a": stats_a,
        "stats_b": stats_b,
        "groups": groups,
        "grand": {
            "total_a": stats_a["total"],
            "total_b": stats_b["total"] if comparing else None,
        },
        "prev_period_total": prev_total,
        "records": records,
        "source_ids": SOURCE_IDS,
    }
