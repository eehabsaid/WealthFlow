# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
"""
core.py
=======
NOTE: Part of the generate_report_generator package split (see package
__init__.py docstring). GenerateReportGenerator.post() orchestrates the
phases in order: parse request -> data_phase (period + aggregates) ->
build reportlab doc/styles -> section builders append to story -> render
PDF bytes -> HttpResponse.
"""
from core.reports.report_utils import get_translations, get_text
from core.reports.generate_report_generator.context import ReportContext
from core.reports.generate_report_generator.data_phase import build_report_data
from core.reports.generate_report_generator import styles as styles_mod
from core.reports.generate_report_generator.section_summary import append_cover_and_summary
from core.reports.generate_report_generator.section_categories import append_category_section
from core.reports.generate_report_generator.section_expenses import append_expense_section
from core.reports.generate_report_generator.section_footer import append_footer_section


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
        from django.http import HttpResponse, JsonResponse

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate
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

        report_data = build_report_data(data, lang, t)
        ctx = ReportContext(lang=lang, t=t, pdf_font=pdf_font, pdf_font_bold=pdf_font_bold, **report_data)

        palette = styles_mod.build_colors()
        ctx.colors = palette
        ctx.styles = styles_mod.build_styles(pdf_font, lang, palette)

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

        def pdf_t(key, default=""):
            return process_pdf_text(get_text(key, lang, t, default))

        append_cover_and_summary(ctx, pdf_t)
        append_category_section(ctx, pdf_t)
        append_expense_section(ctx, pdf_t)
        append_footer_section(ctx)

        doc.build(ctx.story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{ctx.filename}"'
        return response
