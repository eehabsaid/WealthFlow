"""Income Analytics Excel export (openpyxl)."""
import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment

from core.reports.excel_formatting_helpers import _f, _fill, auto_adjust_columns, fmt_base
from core.reports.income_export.context import (
    SOURCE_COLORS,
    income_filename,
    income_item_label,
    income_period_label,
    income_source_label,
)


def _hex(color):
    return "FF" + str(color).lstrip("#").upper()


def _money(ws, row, col, value):
    c = ws.cell(row=row, column=col, value=round(float(value), 2))
    c.number_format = fmt_base()
    return c


def _header_cell(ws, row, col, text, fill=None):
    c = ws.cell(row=row, column=col, value=text)
    c.font = _f(bold=True, color="FFFFFFFF")
    c.fill = _fill(fill or "FF203864")
    c.alignment = Alignment(horizontal="center", vertical="center")
    return c


def _title_block(ws, ctx):
    t = ctx["t"]
    ws.cell(row=1, column=1, value=t.get("income_title", "Income Analytics")).font = _f(bold=True, size=14)
    ws.cell(row=2, column=1, value=t.get("income_period", "Period") + ": " + income_period_label(ctx["data"])).font = _f(size=11)
    ws.cell(row=3, column=1, value=t.get("income_generated", "Generated") + ": " + datetime.date.today().strftime("%Y-%m-%d")).font = _f(size=10, color="FF7F7F7F")


def _summary_sheet(wb, ctx):
    t = ctx["t"]
    d = ctx["data"]
    ws = wb.active
    ws.title = "Summary"
    _title_block(ws, ctx)
    sa = d["stats_a"]
    row = 5
    for label, value in (
        (t.get("income_total", "Total income"), sa["total"]),
        (t.get("income_avg", "Average per month"), round(sa["total"] / sa["active_months"], 2) if sa["active_months"] else 0),
        (t.get("income_best", "Best month"), sa["best_month_total"] or 0),
        (t.get("income_records", "Records"), sa["records"]),
    ):
        ws.cell(row=row, column=1, value=label).font = _f(bold=True)
        c = ws.cell(row=row, column=2, value=value)
        if isinstance(value, float):
            c.number_format = fmt_base()
        row += 1
    row += 1
    ws.cell(row=row, column=1, value=t.get("income_sources", "Income sources")).font = _f(bold=True, size=12)
    row += 1
    _header_cell(ws, row, 1, t.get("income_source", "Source"))
    _header_cell(ws, row, 2, t.get("income_amount", "Amount"))
    _header_cell(ws, row, 3, t.get("income_share", "Share"))
    total = sa["total"] or 1
    for s in d["sources"]:
        row += 1
        ws.cell(row=row, column=1, value=income_source_label(t, s["id"])).fill = _fill(_hex(SOURCE_COLORS[s["id"]]))
        _money(ws, row, 2, s["total"])
        ws.cell(row=row, column=3, value=round(s["total"] / total * 100, 1)).number_format = "0.0"
    ws.freeze_panes = "A6"
    auto_adjust_columns(ws)
    return ws


def _breakdown_sheet(wb, ctx):
    t = ctx["t"]
    d = ctx["data"]
    ws = wb.create_sheet("Breakdown")
    _title_block(ws, ctx)
    comparing = d["grand"]["total_b"] is not None
    row = 5
    if comparing:
        pa, pb = d["periods"]
        labels = [
            t.get("income_item", "Item"),
            str(pa["year"]) + (f"-{pa['month']:02d}" if pa["month"] else ""),
            str(pb["year"]) + (f"-{pb['month']:02d}" if pb["month"] else ""),
            t.get("income_change", "Change"),
            "%",
        ]
    else:
        labels = [
            t.get("income_item", "Item"),
            t.get("income_count", "Records"),
            t.get("income_amount", "Amount"),
            t.get("income_share", "Share"),
        ]
    for i, lab in enumerate(labels, start=1):
        _header_cell(ws, row, i, lab)
    total = d["stats_a"]["total"] or 1
    for g in d["groups"]:
        row += 1
        c = ws.cell(row=row, column=1, value=income_source_label(t, g["source"]))
        c.font = _f(bold=True)
        c.fill = _fill(_hex(SOURCE_COLORS[g["source"]]))
        for i in range(2, len(labels) + 1):
            ws.cell(row=row, column=i).fill = _fill(_hex(SOURCE_COLORS[g["source"]]))
        for it in g["items"]:
            row += 1
            ws.cell(row=row, column=1, value="    " + income_item_label(t, g["source"], it["key"])).font = _f(color="FF404040")
            if comparing:
                _money(ws, row, 2, it["amount_a"])
                _money(ws, row, 3, it["amount_b"])
                _money(ws, row, 4, round(it["amount_b"] - it["amount_a"], 2))
                ws.cell(row=row, column=5, value=round((it["amount_b"] - it["amount_a"]) / abs(it["amount_a"]) * 100, 1) if it["amount_a"] else None).number_format = "0.0"
            else:
                ws.cell(row=row, column=2, value=it["count_a"])
                _money(ws, row, 3, it["amount_a"])
                ws.cell(row=row, column=4, value=round(it["amount_a"] / total * 100, 1)).number_format = "0.0"
        row += 1
        c = ws.cell(row=row, column=1, value=t.get("income_subtotal", "Subtotal") + " — " + income_source_label(t, g["source"]))
        c.font = _f(bold=True)
        if comparing:
            _money(ws, row, 2, g["amount_a"])
            _money(ws, row, 3, g["amount_b"])
            _money(ws, row, 4, round(g["amount_b"] - g["amount_a"], 2))
        else:
            ws.cell(row=row, column=2, value=g["count_a"])
            _money(ws, row, 3, g["amount_a"])
            ws.cell(row=row, column=4, value=round(g["amount_a"] / total * 100, 1)).number_format = "0.0"
    row += 1
    ws.cell(row=row, column=1, value=t.get("income_grand", "Total income")).font = _f(bold=True, size=12)
    if comparing:
        _money(ws, row, 2, d["grand"]["total_a"])
        _money(ws, row, 3, d["grand"]["total_b"])
        _money(ws, row, 4, round(d["grand"]["total_b"] - d["grand"]["total_a"], 2))
    else:
        ws.cell(row=row, column=2, value=d["stats_a"]["records"])
        _money(ws, row, 3, d["grand"]["total_a"])
    ws.freeze_panes = "A6"
    auto_adjust_columns(ws)
    return ws


def _records_sheet(wb, ctx):
    t = ctx["t"]
    d = ctx["data"]
    ws = wb.create_sheet("Records")
    _title_block(ws, ctx)
    row = 5
    for i, lab in enumerate(
        [t.get("income_source", "Source"), t.get("income_period", "Period"), t.get("income_date", "Date"), t.get("income_ref", "Reference"), t.get("income_amount", "Amount")],
        start=1,
    ):
        _header_cell(ws, row, i, lab)
    for r in d["records"]:
        row += 1
        ws.cell(row=row, column=1, value=income_source_label(t, r["source"]))
        ws.cell(row=row, column=2, value=r["period"])
        ws.cell(row=row, column=3, value=r["date"])
        ws.cell(row=row, column=4, value=r["ref"])
        _money(ws, row, 5, r["amount"])
    ws.freeze_panes = "A6"
    auto_adjust_columns(ws)
    return ws


def income_excel_response(user, query):
    from core.reports.income_export.context import income_export_context

    class _Req:
        def __init__(self, user, query):
            self.user = user
            self.GET = query

    ctx = income_export_context(_Req(user, query))
    wb = Workbook()
    _summary_sheet(wb, ctx)
    _breakdown_sheet(wb, ctx)
    _records_sheet(wb, ctx)
    for ws in wb.worksheets:
        ws.sheet_view.rightToLeft = ctx["lang"] == "ar"
    buf = BytesIO()
    wb.save(buf)
    from django.http import HttpResponse

    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="%s"' % income_filename(ctx["data"], ctx["lang"], "xlsx")
    return resp
