"""Expense views: every shape an expense answer can take, built from aggregates / owner-scoped rows."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Q, Sum

from ..labels import month_label, range_label, t
from ..spec import QueryResult, Row
from .common import MAX_ROWS, cell, money


def base_qs(user: Any, months: list[tuple[int, int]], category: str = ""):
    from core.models import Expense

    cond = Q()
    for y, m in months:
        cond |= Q(year=y, month=m)
    qs = Expense.objects.filter(owner=user).filter(cond) if months else Expense.objects.filter(owner=user)
    return qs.filter(category__name=category) if category else qs


def month_totals(qs) -> dict[tuple[int, int], tuple[float, int]]:
    return {(r["year"], r["month"]): (float(r["s"] or 0), r["n"]) for r in
            qs.values("year", "month").annotate(s=Sum("amount_base"), n=Count("id"))}


def cat_totals(qs, by_month: bool = False) -> dict:
    keys = ("year", "month", "category__name") if by_month else ("category__name",)
    out: dict = {}
    for r in qs.values(*keys).annotate(s=Sum("amount_base"), n=Count("id")):
        out[tuple(r[k] for k in keys)] = (float(r["s"] or 0), r["n"])
    return out


def _labels(lang: str, months: list[tuple[int, int]]) -> str:
    return ", ".join(month_label(lang, y, m, abbr=True) for y, m in months) if len(months) <= 6 else range_label(lang, months)


def _uncat(lang: str, name: Any) -> str:
    return cell(name) if name else t(lang, "uncategorized")


def total_sentence(lang, months, total, n, cur, category=""):
    label, head = range_label(lang, months), t(lang, "head_tx", amount=money(total, cur), n=n)
    if not n:
        return QueryResult(intro=t(lang, "exp_none", label=label), facts={"total": 0.0, "count": 0})
    key = "exp_total_cat" if category else "exp_total"
    return QueryResult(intro=t(lang, key, label=label, head=head, cat=category),
                       facts={"total": total, "count": n, "currency": cur, "label": label})


def by_month(lang, months, totals, cur):
    rows, grand, grand_n = [], 0.0, 0
    for y, m in months:
        s, n = totals.get((y, m), (0.0, 0))
        grand, grand_n = grand + s, grand_n + n
        rows.append(Row([month_label(lang, y, m, abbr=True), str(n), money(s, cur)]))
    rows.append(Row([t(lang, "grand"), str(grand_n), money(grand, cur)], bold=True))
    head = t(lang, "head_tx", amount=money(grand, cur), n=grand_n)
    return QueryResult(intro=t(lang, "exp_month", label=range_label(lang, months), head=head, cur=cur),
                       columns=[t(lang, "col_month"), t(lang, "col_tx"), t(lang, "col_amount")], rows=rows,
                       facts={"groups": {f"{y}-{m:02d}": totals.get((y, m), (0.0, 0))[0] for y, m in months}, "total": grand, "currency": cur})


def category_single(lang, month, cats, cur):
    label = month_label(lang, *month)
    total, n = sum(v[0] for v in cats.values()), sum(v[1] for v in cats.values())
    if not n:
        return QueryResult(intro=t(lang, "exp_none", label=label))
    head = t(lang, "head_tx", amount=money(total, cur), n=n)
    rows = [Row([_uncat(lang, k[0]), money(v[0], cur), f"{(v[0] / total * 100 if total else 0):.1f}%", str(v[1])])
            for k, v in sorted(cats.items(), key=lambda x: x[1][0], reverse=True)]
    return QueryResult(intro=t(lang, "exp_cat", label=label, head=head),
                       columns=[t(lang, "col_category"), t(lang, "col_total"), t(lang, "col_share"), t(lang, "col_tx")], rows=rows,
                       facts={"groups": {_uncat(lang, k[0]): v[0] for k, v in cats.items()}, "total": total, "currency": cur})


def category_multi(lang, months, cats, cur):
    rows, grand, grand_n, empty = [], 0.0, 0, []
    for y, m in months:
        label = month_label(lang, y, m, abbr=True)
        mine = {k[2]: v for k, v in cats.items() if (k[0], k[1]) == (y, m)}
        s, n = sum(v[0] for v in mine.values()), sum(v[1] for v in mine.values())
        grand, grand_n = grand + s, grand_n + n
        empty += [] if n else [label]
        rows += [Row([label, _uncat(lang, k), str(v[1]), money(v[0], cur)]) for k, v in sorted(mine.items(), key=lambda x: x[1][0], reverse=True)]
        rows.append(Row([t(lang, "total_of", label=label), "", str(n), money(s, cur)], bold=True))
    rows.append(Row([t(lang, "grand"), "", str(grand_n), money(grand, cur)], bold=True))
    return QueryResult(intro=t(lang, "exp_table", label=_labels(lang, months), n=grand_n, cur=cur),
                       columns=[t(lang, "col_month"), t(lang, "col_category"), t(lang, "col_tx"), t(lang, "col_amount")], rows=rows,
                       footer=t(lang, "exp_empty_note", labels=", ".join(empty)) if empty else "", facts={"total": grand, "currency": cur})


def transactions(lang, months, qs, totals, cur):
    rows, grand, grand_n, empty, shown = [], 0.0, 0, [], 0
    by_ym: dict = {}
    for e in qs.select_related("category").order_by("date", "id").iterator(chunk_size=500):
        by_ym.setdefault((e.year, e.month), []).append(e)
    for y, m in months:
        label = month_label(lang, y, m, abbr=True)
        s, n = totals.get((y, m), (0.0, 0))
        grand, grand_n = grand + s, grand_n + n
        empty += [] if n else [label]
        for e in by_ym.get((y, m), []):
            if shown >= MAX_ROWS:
                break
            shown += 1
            cat = e.category.name if e.category else ""
            rows.append(Row([label, e.date.isoformat() if e.date else "", _uncat(lang, cat),
                             cell(e.description or getattr(e, "notes", "") or "", 50), money(float(e.amount_base or 0), cur)]))
        rows.append(Row([t(lang, "total_of", label=label), "", "", "", money(s, cur)], bold=True))
    rows.append(Row([t(lang, "grand"), "", "", "", money(grand, cur)], bold=True))
    notes = ([t(lang, "exp_empty_note", labels=", ".join(empty))] if empty else []) + \
            ([t(lang, "exp_capped", shown=shown, n=grand_n)] if grand_n > shown else [])
    return QueryResult(intro=t(lang, "exp_table", label=_labels(lang, months), n=grand_n, cur=cur),
                       columns=[t(lang, "col_month"), t(lang, "col_date"), t(lang, "col_category"), t(lang, "col_desc"), t(lang, "col_amount")],
                       rows=rows, footer="\n\n".join(notes), facts={"total": grand, "currency": cur})


def daily(lang, months, qs, cur):
    days: dict[str, list] = {}
    for e in qs.select_related("category").order_by("date", "id").iterator(chunk_size=500):
        days.setdefault(e.date.isoformat() if e.date else t(lang, "no_date"), []).append(e)
    total = sum(float(e.amount_base or 0) for es in days.values() for e in es)
    n = sum(len(es) for es in days.values())
    label = range_label(lang, months)
    if not n:
        return QueryResult(intro=t(lang, "exp_none", label=label))
    rows = []
    for day, es in list(days.items())[:MAX_ROWS]:
        det = "; ".join(f"{cell((e.category.name if e.category else t(lang, 'uncategorized')) + (': ' + e.description if e.description else ''))} "
                        f"{float(e.amount_base or 0):,.2f}" for e in es)
        rows.append(Row([day, money(sum(float(e.amount_base or 0) for e in es), cur), det]))
    head = t(lang, "head_tx", amount=money(total, cur), n=n)
    return QueryResult(intro=t(lang, "exp_daily", label=label, head=head),
                       columns=[t(lang, "col_date"), t(lang, "col_total"), t(lang, "col_details")], rows=rows,
                       facts={"total": total, "count": n, "currency": cur})


def item_rows(lang, qs, cur) -> list[Row]:
    return [Row([e.date.isoformat() if e.date else "", _uncat(lang, e.category.name if e.category else ""),
                 cell(e.description or "", 50), money(float(e.amount_base or 0), cur)]) for e in qs.select_related("category")]
