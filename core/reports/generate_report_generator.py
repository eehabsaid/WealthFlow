# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
from core.models import Expense, BankCertificate
from core.utils.date_formatter import format_date
from core.reports.report_utils import get_translations, format_arabic, get_text

class GenerateReportGenerator(object):
    """
    POST /api/reports/generate/
    body: { type: "monthly"|"yearly"|"custom",
            year: 2026, month: 5,       # for monthly
            start_date: "2026-01-01",   # for custom
            end_date:   "2026-05-31" }
    Returns: PDF file
    """

    def post(self, request):
        import json as _json
        import datetime
        from django.http import HttpResponse, JsonResponse

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                HRFlowable,
            )
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
            import io
        except ImportError:
            return JsonResponse(
                {"error": "reportlab not installed. Run: pip install reportlab"},
                status=500,
            )

        data = _json.loads(request.body)
        lang = data.get("lang", "en")
        t = get_translations(lang)

        from core.reports.pdf_font_utils import get_arabic_pdf_font, process_pdf_text
        pdf_font, pdf_font_bold = get_arabic_pdf_font()

        rtype = data.get("type", "monthly")
        year = int(data.get("year", datetime.date.today().year))
        month = int(data.get("month", datetime.date.today().month))

        # Accept both parameter styles (with or without suffix) to be fully secure
        start_date = data.get("start_date") or data.get("start")
        end_date = data.get("end_date") or data.get("end")

        # ── Filter expenses safely across all field schemas ──
        qs = Expense.objects.select_related("category", "subcategory").all()
        if rtype == "monthly":
            qs = qs.filter(year=year, month=month)
            json_month_key = f"month_short_{month}"
            translated_month = t.get(json_month_key) or t.get(
                f"month_{datetime.date(year, month, 1).strftime('%B').lower()}",
                datetime.date(year, month, 1).strftime("%B"),
            )

            title_str = f"{t.get('monthly_report', 'Monthly Report')} - {translated_month} {year}"
            filename = f"report_{year}_{month:02d}.pdf"
        elif rtype == "yearly":
            qs = qs.filter(year=year)
            title_str = f"{t.get('yearly_report', 'Yearly Report')} - {year}"
            filename = f"report_{year}.pdf"
        else:
            from datetime import date as _date

            sd = _date.fromisoformat(start_date)
            ed = _date.fromisoformat(end_date)
            qs = qs.filter(date__gte=sd, date__lte=ed)

            title_str = f"{t.get('report', 'Report')} {start_date} {t.get('to', 'to')} {end_date}"
            filename = f"report_{start_date}_{end_date}.pdf"

        if lang == "ar":
            title_str = format_arabic(title_str)

        expenses = list(qs)
        total_exp = sum(float(e.amount_egp) for e in expenses)

        # Income for period (salary paid amounts)
        from core.services.reports.report_service import ReportService
        total_inc = ReportService.get_period_income(rtype, year, month, start_date, end_date)

        # 2. Add Bank Interest (Summing all certificates)
        total_interest = sum(
            float(c.interest_value or 0) for c in BankCertificate.objects.all()
        )
        total_inc += total_interest

        # 3. Final Calculations
        net_sav = total_inc - total_exp
        sav_rate = (net_sav / total_inc * 100) if total_inc > 0 else 0

        # Category breakdown
        cat_totals = {}
        for e in expenses:
            cname = e.category.name if e.category else "Uncategorised"
            cat_totals[cname] = cat_totals.get(cname, 0) + float(e.amount_egp)

        # ── Build PDF ──
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        getSampleStyleSheet()
        navy = colors.HexColor("#000080")
        blue = colors.HexColor("#1a6ef5")
        green = colors.HexColor("#00d68f")
        red = colors.HexColor("#ff4d6d")
        grey = colors.HexColor("#7b97cc")

        H1 = ParagraphStyle(
            "H1",
            fontSize=22,
            textColor=blue,
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName=pdf_font,
        )
        H11 = ParagraphStyle(
            "H11",
            fontSize=18,
            textColor=navy,
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName=pdf_font,
        )
        H2 = ParagraphStyle(
            "H2",
            fontSize=14,
            textColor=navy,
            spaceAfter=4,
            spaceBefore=12,
            fontName=pdf_font,
        )

        story = []

        def pdf_t(key, default=""):
            return process_pdf_text(get_text(key, lang, t, default))

        # Cover
        story.append(Spacer(1, 1 * cm))
        report_text = pdf_t("financial_report", "Financial Report")

        story.append(Paragraph(process_pdf_text(report_text), H1))
        story.append(Paragraph(process_pdf_text(title_str), H11))
        story.append(HRFlowable(width="100%", thickness=1, color=blue))
        story.append(Spacer(1, 0.5 * cm))
        table_title_style = ParagraphStyle(
            "TableTitle", parent=H2, alignment=TA_RIGHT if lang == "ar" else TA_LEFT
        )
        story.append(
            Paragraph(pdf_t("summary", "Summary"), table_title_style)
        )

        cell_L = ParagraphStyle(
            "CellL", fontName=pdf_font, fontSize=10, textColor=navy, alignment=TA_LEFT
        )
        cell_R = ParagraphStyle(
            "CellR", fontName=pdf_font, fontSize=10, textColor=navy, alignment=TA_RIGHT
        )
        cell_HL = ParagraphStyle(
            "CellHL",
            fontName=pdf_font,
            fontSize=10,
            textColor=colors.white,
            alignment=TA_LEFT,
        )
        cell_HR = ParagraphStyle(
            "CellHR",
            fontName=pdf_font,
            fontSize=10,
            textColor=colors.white,
            alignment=TA_RIGHT,
        )

        kpi_data = [
            [
                Paragraph(pdf_t("metric", "Metric"), cell_HL),
                Paragraph(pdf_t("amount", "Amount (EGP)"), cell_HR),
            ],
            [
                Paragraph(pdf_t("total_income", "Total Income"), cell_L),
                Paragraph(f"{total_inc:,.2f}", cell_R),
            ],
            [
                Paragraph(
                    pdf_t("total_expenses", "Total Expenses"), cell_L
                ),
                Paragraph(f"{total_exp:,.2f}", cell_R),
            ],
            [
                Paragraph(pdf_t("net_savings", "Net Savings"), cell_L),
                Paragraph(
                    f"{net_sav:,.2f}",
                    ParagraphStyle(
                        "NetSavR",
                        parent=cell_R,
                        textColor=green if net_sav >= 0 else red,
                    ),
                ),
            ],
            [
                Paragraph(pdf_t("savings_rate", "Savings Rate"), cell_L),
                Paragraph(f"{sav_rate:.1f}%", cell_R),
            ],
        ]

        kpi_table = Table(kpi_data, colWidths=[9 * cm, 7 * cm])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), blue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), pdf_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#f0f4ff"), colors.white],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a6e")),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 0.5 * cm))

        # Category breakdown
        if cat_totals:
            story.append(
                Paragraph(
                    pdf_t("cat_breakdown", "Expense Breakdown by Category"),
                    table_title_style,
                )
            )

            cell_L9 = ParagraphStyle(
                "CellL9",
                fontName=pdf_font,
                fontSize=9,
                textColor=navy,
                alignment=TA_LEFT,
            )
            cell_R9 = ParagraphStyle(
                "CellR9",
                fontName=pdf_font,
                fontSize=9,
                textColor=navy,
                alignment=TA_RIGHT,
            )
            cell_HL9 = ParagraphStyle(
                "CellHL9",
                fontName=pdf_font,
                fontSize=9,
                textColor=colors.white,
                alignment=TA_LEFT,
            )
            cell_HR9 = ParagraphStyle(
                "CellHR9",
                fontName=pdf_font,
                fontSize=9,
                textColor=colors.white,
                alignment=TA_RIGHT,
            )

            cat_data = [
                [
                    Paragraph(pdf_t("category", "Category"), cell_HL9),
                    Paragraph(pdf_t("amount", "Amount (EGP)"), cell_HR9),
                    Paragraph(pdf_t("pct", "% of Total"), cell_HR9),
                ]
            ]

            for cname, ctotal in sorted(cat_totals.items(), key=lambda x: -x[1]):
                pct = (ctotal / total_exp * 100) if total_exp > 0 else 0
                display_cname = process_pdf_text(cname)

                cat_data.append(
                    [
                        Paragraph(display_cname, cell_L9),
                        Paragraph(f"{ctotal:,.2f}", cell_R9),
                        Paragraph(f"{pct:.1f}%", cell_R9),
                    ]
                )

            cat_data.append(
                [
                    Paragraph(pdf_t("total", "TOTAL"), cell_L9),
                    Paragraph(f"{total_exp:,.2f}", cell_R9),
                    Paragraph("100%", cell_R9),
                ]
            )

            cat_table = Table(cat_data, colWidths=[9 * cm, 5 * cm, 3 * cm])
            cat_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), blue),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, -1),
                            pdf_font,
                        ),
                        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0fe")),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -2),
                            [colors.HexColor("#f0f4ff"), colors.white],
                        ),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a6e")),
                        ("PADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(cat_table)
            story.append(Spacer(1, 0.5 * cm))

        # Detailed expense entries
        if expenses:
            story.append(
                Paragraph(
                    pdf_t("expense_entries", "Expense Entries"),
                    table_title_style,
                )
            )

            cell_L8 = ParagraphStyle(
                "CellL8",
                fontName=pdf_font,
                fontSize=8,
                textColor=navy,
                alignment=TA_LEFT,
            )
            cell_R8 = ParagraphStyle(
                "CellR8",
                fontName=pdf_font,
                fontSize=8,
                textColor=navy,
                alignment=TA_RIGHT,
            )
            cell_HL8 = ParagraphStyle(
                "CellHL8",
                fontName=pdf_font,
                fontSize=8,
                textColor=colors.white,
                alignment=TA_LEFT,
            )
            cell_HR8 = ParagraphStyle(
                "CellHR8",
                fontName=pdf_font,
                fontSize=8,
                textColor=colors.white,
                alignment=TA_RIGHT,
            )

            exp_data = [
                [
                    Paragraph(pdf_t("date", "Date"), cell_HL8),
                    Paragraph(pdf_t("category", "Category"), cell_HL8),
                    Paragraph(
                        pdf_t("description", "Description"), cell_HL8
                    ),
                    Paragraph(pdf_t("method", "Method"), cell_HL8),
                    Paragraph(pdf_t("amount", "Amount"), cell_HR8),
                ]
            ]

            for e in sorted(expenses, key=lambda x: x.date):
                cname = e.category.name if e.category else "—"
                desc = e.description or "—"
                method = e.payment_method or "—"

                cname = process_pdf_text(cname)
                desc = process_pdf_text(desc[:40])
                method = process_pdf_text(method)

                exp_data.append(
                    [
                        Paragraph(format_date(e.date, lang), cell_L8),
                        Paragraph(cname, cell_L8),
                        Paragraph(desc, cell_L8),
                        Paragraph(method, cell_L8),
                        Paragraph(f"{float(e.amount):,.2f}", cell_R8),
                    ]
                )

            exp_table = Table(
                exp_data, colWidths=[2.5 * cm, 3.5 * cm, 6 * cm, 3 * cm, 3 * cm]
            )
            exp_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), blue),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, -1),
                            pdf_font,
                        ),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.HexColor("#f0f4ff"), colors.white],
                        ),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#1e3a6e")),
                        ("PADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(exp_table)

        # Footer
        story.append(Spacer(1, 1 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=grey))

        today = datetime.date.today()
        f_day = today.day
        f_year = today.year
        f_month_name = today.strftime("%B")

        f_json_key = f"month_{f_month_name.lower()}"
        f_translated_month = t.get(f_json_key)

        if not f_translated_month:
            if lang == "ar":
                ARABIC_MONTHS = {
                    "January": "يناير",
                    "February": "فبراير",
                    "March": "مارس",
                    "April": "أبريل",
                    "May": "مايو",
                    "June": "يونيو",
                    "July": "يوليو",
                    "August": "أغسطس",
                    "September": "سبتمبر",
                    "October": "أكتوبر",
                    "November": "نوفمبر",
                    "December": "ديسمبر",
                }
                f_translated_month = ARABIC_MONTHS.get(f_month_name, f_month_name)
            else:
                f_translated_month = f_month_name

        raw_label = t.get("generated_by", "Generated by WealthFlow")

        if lang == "ar":
            raw_footer = f"{raw_label} - {f_day} {f_translated_month} {f_year}"
            footer_text = format_arabic(raw_footer)
        else:
            footer_text = f"{raw_label} - {f_day} {f_translated_month} {f_year}"

        story.append(
            Paragraph(
                footer_text,
                ParagraphStyle(
                    "F",
                    fontSize=8,
                    textColor=grey,
                    alignment=TA_CENTER,
                    fontName=pdf_font,
                ),
            )
        )

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
