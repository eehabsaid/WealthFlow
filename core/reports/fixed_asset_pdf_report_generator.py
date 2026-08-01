import io
from django.http import HttpResponse, JsonResponse
from core.models import FixedAsset
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)

from core.reports.fixed_asset_report_helpers import (
    fixed_asset_report_context as _fixed_asset_report_context,
    fixed_asset_report_label as _fixed_asset_report_label,
    fixed_asset_user_text as _fixed_asset_user_text,
    fixed_asset_pdf_table as _fixed_asset_pdf_table,
    build_fixed_asset_pdf_story as _build_fixed_asset_pdf_story,
)

class FixedAssetPdfReportGenerator(object):

    def get(self, request):
        try:
            context = _fixed_asset_report_context(request)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except FixedAsset.DoesNotExist:
            return JsonResponse({"error": "No fixed assets found"}, status=404)

        lang = context["lang"]
        t = context["t"]
        assets = context["assets"]
        scope = context["scope"]
        portfolio_snapshot = context.get("portfolio_snapshot") or {}

        from core.reports.pdf_font_utils import get_arabic_pdf_font
        font_name, font_name_bold = get_arabic_pdf_font()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "FixedAssetTitle",
            parent=styles["Heading1"],
            fontName=font_name_bold,
            fontSize=16,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=8,
        )
        heading_style = ParagraphStyle(
            "FixedAssetHeading",
            parent=styles["Heading2"],
            fontName=font_name_bold,
            fontSize=12,
            textColor=colors.HexColor("#1a6ef5"),
            spaceBefore=4,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "FixedAssetBody",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=9,
            textColor=colors.HexColor("#1f2937"),
            leading=11,
        )

        report_title = _fixed_asset_report_label(
            t,
            lang,
            "fixed_assets_report_title",
            "Fixed Assets Report",
        )
        if scope == "single":
            report_title = f"{report_title} - {_fixed_asset_user_text(assets[0].name, lang)}"

        from core.reports.pdf_font_utils import process_pdf_text

        story = [Paragraph(process_pdf_text(report_title), title_style), Spacer(1, 0.35 * cm)]

        if scope == "portfolio":
            summary_rows = [
                [
                    _fixed_asset_report_label(t, lang, "total_fixed_assets_value", "Total Fixed Assets"),
                    f"{float(portfolio_snapshot.get('total_fixed_assets_value') or 0):,.2f}",
                ],
                [
                    _fixed_asset_report_label(t, lang, "net_worth", "Net Worth"),
                    f"{float(portfolio_snapshot.get('total_net_worth') or 0):,.2f}",
                ],
                [
                    _fixed_asset_report_label(t, lang, "net_worth_contribution", "Net Worth Contribution"),
                    f"{float(portfolio_snapshot.get('net_worth_contribution') or 0):,.2f}%",
                ],
            ]
            story.append(Paragraph(process_pdf_text(_fixed_asset_report_label(t, lang, "portfolio_distribution", "Portfolio Distribution")), heading_style))
            story.append(_fixed_asset_pdf_table(summary_rows, [7 * cm, 8.5 * cm], font_name))
            story.append(Spacer(1, 0.35 * cm))

        for index, asset in enumerate(assets):
            story.extend(
                _build_fixed_asset_pdf_story(
                    asset,
                    lang,
                    t,
                    styles,
                    title_style,
                    heading_style,
                    body_style,
                    font_name,
                )
            )
            if index < len(assets) - 1:
                story.append(PageBreak())

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        filename = (
            f"fixed_asset_{assets[0].id}_report.pdf"
            if scope == "single"
            else "fixed_assets_portfolio_report.pdf"
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
