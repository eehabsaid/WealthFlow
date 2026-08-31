"""
section_expenses.py
====================
NOTE: Part of the generate_report_generator package split (see package
__init__.py docstring). Appends the detailed "Expense Entries" table to
ctx.story, sorted by date.
"""
from core.reports.pdf_font_utils import process_pdf_text
from core.utils.date_formatter import format_date


def append_expense_section(ctx, pdf_t):
    if not ctx.expenses:
        return

    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table, TableStyle

    palette = ctx.colors
    s = ctx.styles
    cell = s["cell8"]

    ctx.story.append(Paragraph(pdf_t("expense_entries", "Expense Entries"), s["table_title"]))

    exp_data = [
        [
            Paragraph(pdf_t("date", "Date"), cell["HL"]),
            Paragraph(pdf_t("category", "Category"), cell["HL"]),
            Paragraph(pdf_t("description", "Description"), cell["HL"]),
            Paragraph(pdf_t("method", "Method"), cell["HL"]),
            Paragraph(pdf_t("amount", "Amount"), cell["HR"]),
        ]
    ]

    for e in sorted(ctx.expenses, key=lambda x: x.date):
        cname = process_pdf_text(e.category.name if e.category else "—")
        desc = process_pdf_text((e.description or "—")[:40])
        method = process_pdf_text(e.payment_method or "—")

        exp_data.append(
            [
                Paragraph(format_date(e.date, ctx.lang), cell["L"]),
                Paragraph(cname, cell["L"]),
                Paragraph(desc, cell["L"]),
                Paragraph(method, cell["L"]),
                Paragraph(f"{float(e.amount):,.2f}", cell["R"]),
            ]
        )

    exp_table = Table(exp_data, colWidths=[2.5 * cm, 3.5 * cm, 6 * cm, 3 * cm, 3 * cm])
    exp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette["blue"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), palette["white"]),
                ("FONTNAME", (0, 0), (-1, -1), ctx.pdf_font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4ff"), palette["white"]]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1e3a6e")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    ctx.story.append(exp_table)
