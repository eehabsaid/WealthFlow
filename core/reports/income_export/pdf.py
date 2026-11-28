"""Income Analytics PDF export (reportlab, A4, RTL-aware for Arabic)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.reports.pdf_font_utils import get_arabic_pdf_font, process_pdf_text
from core.reports.income_export.context import (
    SOURCE_COLORS,
    income_filename,
    income_item_label,
    income_period_label,
    income_source_label,
)

ACCENT = colors.HexColor("#1a6ef5")
GREY_BG = colors.HexColor("#f3f6fc")
GRID = colors.HexColor("#d7e0ef")


def _hex(color):
    return colors.HexColor("0x" + str(color).lstrip("#"))


def _styles(font):
    return {
        "title": ParagraphStyle("t", fontName=font, fontSize=16, leading=20, textColor=colors.HexColor("#0d1530")),
        "sub": ParagraphStyle("s", fontName=font, fontSize=10, leading=14, textColor=colors.HexColor("#4a6399")),
        "h": ParagraphStyle("h", fontName=font, fontSize=12, leading=15, textColor=colors.HexColor("#0d1530"), spaceBefore=10, spaceAfter=4),
        "cell": ParagraphStyle("c", fontName=font, fontSize=9, leading=12),
    }


def _txt(text):
    return process_pdf_text(str(text))


def _money(v):
    return f"{float(v):,.2f}"


def _kpi_table(story, ctx, st):
    t, d = ctx["t"], ctx["data"]
    sa = d["stats_a"]
    cells = [
        (t.get("income_total", "Total income"), _money(sa["total"])),
        (t.get("income_avg", "Average per month"), _money(sa["total"] / sa["active_months"]) if sa["active_months"] else "0.00"),
        (t.get("income_best", "Best month"), _money(sa["best_month_total"] or 0)),
        (t.get("income_records", "Records"), str(sa["records"])),
    ]
    rows = [[Paragraph(_txt(l), st["sub"]) for l, _ in cells], [Paragraph(_txt(v), st["cell"]) for _, v in cells]]
    table = Table(rows, colWidths=[3.9 * cm] * 4)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREY_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))


def _source_table(story, ctx, st):
    t, d = ctx["t"], ctx["data"]
    total = d["stats_a"]["total"] or 1
    rows = [[Paragraph(_txt(t.get("income_source", "Source")), st["cell"]), Paragraph(_txt(t.get("income_amount", "Amount")), st["cell"]), Paragraph(_txt(t.get("income_share", "Share")), st["cell"])]]
    for s in d["sources"]:
        rows.append([
            Paragraph(_txt(income_source_label(t, s["id"])), st["cell"]),
            Paragraph(_txt(_money(s["total"])), st["cell"]),
            Paragraph(_txt(f"{s['total'] / total * 100:.1f}%"), st["cell"]),
        ])
    table = Table(rows, colWidths=[6 * cm, 5 * cm, 4 * cm])
    style = [("BACKGROUND", (0, 0), (-1, 0), ACCENT), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("GRID", (0, 0), (-1, -1), 0.5, GRID), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for i, s in enumerate(d["sources"], start=1):
        style.append(("BACKGROUND", (0, i), (0, i), _hex(SOURCE_COLORS[s["id"]])))
    table.setStyle(TableStyle(style))
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))


def _breakdown(story, ctx, st, bold_font):
    t, d = ctx["t"], ctx["data"]
    comparing = d["grand"]["total_b"] is not None
    story.append(Paragraph(_txt(t.get("income_breakdown", "Detailed breakdown")), st["h"]))
    rows = []
    style = []
    for g in d["groups"]:
        if comparing:
            rows.append([Paragraph(_txt(income_source_label(t, g["source"])), st["cell"]), Paragraph(_txt(_money(g["amount_a"])), st["cell"]), Paragraph(_txt(_money(g["amount_b"])), st["cell"]), Paragraph(_txt(_money(g["amount_b"] - g["amount_a"])), st["cell"])])
        else:
            rows.append([Paragraph(_txt(income_source_label(t, g["source"])), st["cell"]), Paragraph(_txt(str(g["count_a"])), st["cell"]), Paragraph(_txt(_money(g["amount_a"])), st["cell"])])
        style.append(("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), _hex(SOURCE_COLORS[g["source"]])))
        style.append(("TEXTCOLOR", (0, len(rows) - 1), (-1, len(rows) - 1), colors.white))
        for it in g["items"]:
            label = "    " + income_item_label(t, g["source"], it["key"])
            if comparing:
                rows.append([Paragraph(_txt(label), st["cell"]), Paragraph(_txt(_money(it["amount_a"])), st["cell"]), Paragraph(_txt(_money(it["amount_b"])), st["cell"]), Paragraph(_txt(_money(it["amount_b"] - it["amount_a"])), st["cell"])])
            else:
                rows.append([Paragraph(_txt(label), st["cell"]), Paragraph(_txt(str(it["count_a"])), st["cell"]), Paragraph(_txt(_money(it["amount_a"])), st["cell"])])
        sub = t.get("income_subtotal", "Subtotal") + " — " + income_source_label(t, g["source"])
        if comparing:
            rows.append([Paragraph(_txt(sub), st["cell"]), Paragraph(_txt(_money(g["amount_a"])), st["cell"]), Paragraph(_txt(_money(g["amount_b"])), st["cell"]), Paragraph(_txt(_money(g["amount_b"] - g["amount_a"])), st["cell"])])
        else:
            rows.append([Paragraph(_txt(sub), st["cell"]), Paragraph(_txt(str(g["count_a"])), st["cell"]), Paragraph(_txt(_money(g["amount_a"])), st["cell"])])
        style.append(("FONTNAME", (0, len(rows) - 1), (-1, len(rows) - 1), bold_font))
    grand = t.get("income_grand", "Total income")
    if comparing:
        rows.append([Paragraph(_txt(grand), st["cell"]), Paragraph(_txt(_money(d["grand"]["total_a"])), st["cell"]), Paragraph(_txt(_money(d["grand"]["total_b"])), st["cell"]), Paragraph(_txt(_money(d["grand"]["total_b"] - d["grand"]["total_a"])), st["cell"])])
    else:
        rows.append([Paragraph(_txt(grand), st["cell"]), Paragraph(_txt(str(d["stats_a"]["records"])), st["cell"]), Paragraph(_txt(_money(d["grand"]["total_a"])), st["cell"])])
    style.append(("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), colors.HexColor("#e8f0fe")))
    style.append(("FONTNAME", (0, len(rows) - 1), (-1, len(rows) - 1), bold_font))
    widths = [6.5 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm] if comparing else [8 * cm, 3 * cm, 4.5 * cm]
    table = Table(rows, colWidths=widths)
    table.setStyle(TableStyle(style + [("GRID", (0, 0), (-1, -1), 0.5, GRID), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(table)


def income_pdf_response(user, query):
    from django.http import HttpResponse

    from core.reports.income_export.context import income_export_context

    class _Req:
        def __init__(self, user, query):
            self.user = user
            self.GET = query

    ctx = income_export_context(_Req(user, query))
    t, d = ctx["t"], ctx["data"]
    font, bold_font = get_arabic_pdf_font()
    st = _styles(font)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=t.get("income_title", "Income Analytics"), leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#4a6399"))
        canvas.drawRightString(1.6 * cm, 0.9 * cm, f"{t.get('income_generated', 'Generated')} - {doc_.page}")
        canvas.restoreState()

    story = []
    story.append(Paragraph(_txt("WealthFlow"), st["sub"]))
    story.append(Paragraph(_txt(t.get("income_title", "Income Analytics")), st["title"]))
    story.append(Paragraph(_txt(t.get("income_period", "Period") + ": " + income_period_label(d)), st["sub"]))
    story.append(Spacer(1, 0.3 * cm))
    _kpi_table(story, ctx, st)
    _source_table(story, ctx, st)
    _breakdown(story, ctx, st, bold_font)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = 'attachment; filename="%s"' % income_filename(d, ctx["lang"], "pdf")
    return resp
