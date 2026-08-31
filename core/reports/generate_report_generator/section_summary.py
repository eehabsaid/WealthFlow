"""
section_summary.py
===================
NOTE: Part of the generate_report_generator package split (see package
__init__.py docstring). Appends the cover title block and the KPI summary
table (total income, total expenses, net savings, savings rate) to
ctx.story.
"""
from core.reports.pdf_font_utils import process_pdf_text


def append_cover_and_summary(ctx, pdf_t):
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle

    palette = ctx.colors
    s = ctx.styles
    cell = s["cell10"]

    ctx.story.append(Spacer(1, 1 * cm))
    report_text = pdf_t("financial_report", "Financial Report")
    ctx.story.append(Paragraph(process_pdf_text(report_text), s["H1"]))
    ctx.story.append(Paragraph(process_pdf_text(ctx.title_str), s["H11"]))
    ctx.story.append(HRFlowable(width="100%", thickness=1, color=palette["blue"]))
    ctx.story.append(Spacer(1, 0.5 * cm))
    ctx.story.append(Paragraph(pdf_t("summary", "Summary"), s["table_title"]))

    net_sav_style = ParagraphStyle(
        "NetSavR", parent=cell["R"], textColor=palette["green"] if ctx.net_sav >= 0 else palette["red"]
    )

    kpi_data = [
        [Paragraph(pdf_t("metric", "Metric"), cell["HL"]), Paragraph(pdf_t("amount", "Amount (EGP)"), cell["HR"])],
        [Paragraph(pdf_t("total_income", "Total Income"), cell["L"]), Paragraph(f"{ctx.total_inc:,.2f}", cell["R"])],
        [Paragraph(pdf_t("total_expenses", "Total Expenses"), cell["L"]), Paragraph(f"{ctx.total_exp:,.2f}", cell["R"])],
        [Paragraph(pdf_t("net_savings", "Net Savings"), cell["L"]), Paragraph(f"{ctx.net_sav:,.2f}", net_sav_style)],
        [Paragraph(pdf_t("savings_rate", "Savings Rate"), cell["L"]), Paragraph(f"{ctx.sav_rate:.1f}%", cell["R"])],
    ]

    kpi_table = Table(kpi_data, colWidths=[9 * cm, 7 * cm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette["blue"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), palette["white"]),
                ("FONTNAME", (0, 0), (-1, -1), ctx.pdf_font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4ff"), palette["white"]]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a6e")),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    ctx.story.append(kpi_table)
    ctx.story.append(Spacer(1, 0.5 * cm))
