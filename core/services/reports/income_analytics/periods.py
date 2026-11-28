"""Period resolution and aggregation for Income Analytics (off / yoy / mom)."""
from datetime import date


def parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_months(raw):
    out = set()
    for part in str(raw or "").split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= 12:
            out.add(int(part))
    return sorted(out)


def parse_sources(raw):
    raw = [s.strip() for s in str(raw or "").split(",") if s.strip()]
    return [s for s in raw if s in ("salary", "bonus", "perdiem", "cert", "bank", "rent", "manual", "sale")]


def _years_with_data(rows):
    return sorted({r["year"] for r in rows}, reverse=True)


def _months_with_data(rows):
    pairs = sorted({(r["year"], r["month"]) for r in rows}, reverse=True)
    return pairs


def default_year(rows):
    years = _years_with_data(rows)
    if not years:
        return date.today().year - 1
    for y in years:
        if y < date.today().year:
            return y
    return years[0]


def default_yoy(rows):
    years = _years_with_data(rows)
    yb = years[0] if years else date.today().year
    ya = years[1] if len(years) > 1 else yb
    return ya, yb


def default_mom(rows):
    pairs = _months_with_data(rows)
    if not pairs:
        today = date.today()
        return (today.year, today.month), (today.year, today.month)
    b = pairs[0]
    a = pairs[1] if len(pairs) > 1 else b
    return a, b


def resolve_periods(rows, query):
    mode = query.get("mode") if query.get("mode") in ("off", "yoy", "mom") else "off"
    if mode == "yoy":
        ya, yb = default_yoy(rows)
        ya = parse_int(query.get("ya"), ya)
        yb = parse_int(query.get("yb"), yb)
        return mode, [{"key": "A", "year": ya, "month": None}, {"key": "B", "year": yb, "month": None}]
    if mode == "mom":
        (ya, ma), (yb, mb) = default_mom(rows)
        ma = parse_int(query.get("ma"), ma)
        mya = parse_int(query.get("mya"), ya)
        mb = parse_int(query.get("mb"), mb)
        myb = parse_int(query.get("myb"), yb)
        return mode, [
            {"key": "A", "year": mya, "month": ma},
            {"key": "B", "year": myb, "month": mb},
        ]
    year = parse_int(query.get("year"), default_year(rows))
    return mode, [{"key": "A", "year": year, "month": None}]


def in_period(row, period, months):
    if row["year"] != period["year"]:
        return False
    if period["month"]:
        return row["month"] == period["month"]
    if months and row["month"] not in months:
        return False
    return True


def item_key(row, mode):
    if row["source"] in ("salary", "bonus"):
        if mode == "mom":
            return row["ref"]  # by company
        return "m%02d" % row["month"]
    return row["ref"]


def _item_sort(key):
    if key.startswith("m") and key[1:2].isdigit():
        return (0, int(key[1:]))
    return (1, str(key))


def group_rows(rows_a, rows_b, mode):
    """groups[]: source -> items -> amounts/counts -> subtotal, plus the grand total."""
    sources = [s for s in ("salary", "bonus", "perdiem", "cert", "bank", "rent", "manual", "sale")]
    groups = []
    for src in sources:
        a = [r for r in rows_a if r["source"] == src]
        b = [r for r in rows_b if r["source"] == src]
        if not a and not b:
            continue
        keys = sorted({item_key(r, mode) for r in a + b}, key=_item_sort)
        items = []
        for k in keys:
            ia = [r for r in a if item_key(r, mode) == k]
            ib = [r for r in b if item_key(r, mode) == k]
            items.append({
                "key": k,
                "count_a": len(ia),
                "amount_a": round(sum(r["amount"] for r in ia), 2),
                "count_b": len(ib),
                "amount_b": round(sum(r["amount"] for r in ib), 2),
            })
        groups.append({
            "source": src,
            "items": items,
            "count_a": len(a),
            "amount_a": round(sum(r["amount"] for r in a), 2),
            "count_b": len(b),
            "amount_b": round(sum(r["amount"] for r in b), 2),
        })
    return groups


def period_stats(rows):
    by_month = {}
    for r in rows:
        by_month[r["month"]] = by_month.get(r["month"], 0) + r["amount"]
    active = len(by_month)
    best = max(by_month.items(), key=lambda kv: kv[1]) if by_month else None
    return {
        "total": round(sum(r["amount"] for r in rows), 2),
        "records": len(rows),
        "active_months": active,
        "best_month": best[0] if best else None,
        "best_month_total": round(best[1], 2) if best else None,
        "by_month": {str(m): round(v, 2) for m, v in sorted(by_month.items())},
    }


def source_totals(rows, source_ids):
    out = []
    for s in source_ids:
        amt = [r for r in rows if r["source"] == s]
        out.append({
            "id": s,
            "total": round(sum(r["amount"] for r in amt), 2),
            "records": len(amt),
        })
    return out
