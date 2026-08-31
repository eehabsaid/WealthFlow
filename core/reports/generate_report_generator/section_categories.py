"""
section_categories.py
======================
NOTE: Part of the generate_report_generator package split (see package
__init__.py docstring). Appends the "Expense Breakdown by Category" table
to ctx.story, sorted by amount descending with a TOTAL row.
"""
from core.reports.pdf_font_utils import process_pdf_text


def append_category_section(ctx, pdf_t):
    if not ctx.cat_totals:
        return

    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    palette = ctx.colors
    s = ctx.styles
    cell = s["cell9"]

    ctx.story.append(Paragraph(pdf_t("cat_breakdown", "Expense Breakdown by Category"), s["table_title"]))

    cat_data = [
        [
            Paragraph(pdf_t("category", "Category"), cell["HL"]),
            Paragraph(pdf_t("amount", "Amount (EGP)"), cell["HR"]),
            Paragraph(pdf_t("pct", "% of Total"), cell["HR"]),
        ]
    ]

    for cname, ctotal in sorted(ctx.cat_totals.items(), key=lambda x: -x[1]):
        pct = (ctotal / ctx.total_exp * 100) if ctx.total_exp > 0 else 0
        display_cname = process_pdf_text(cname)
        cat_data.append(
            [
                Paragraph(display_cname, cell["L"]),
                Paragraph(f"{ctotal:,.2f}", cell["R"]),
                Paragraph(f"{pct:.1f}%", cell["R"]),
            ]
        )

    cat_data.append(
        [
            Paragraph(pdf_t("total", "TOTAL"), cell["L"]),
            Paragraph(f"{ctx.total_exp:,.2f}", cell["R"]),
            Paragraph("100%", cell["R"]),
        ]
    )

    cat_table = Table(cat_data, colWidths=[9 * cm, 5 * cm, 3 * cm])
    cat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette["blue"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), palette["white"]),
                ("FONTNAME", (0, 0), (-1, -1), ctx.pdf_font),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0fe")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f0f4ff"), palette["white"]]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a6e")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    ctx.story.append(cat_table)
    ctx.story.append(Spacer(1, 0.5 * cm))
