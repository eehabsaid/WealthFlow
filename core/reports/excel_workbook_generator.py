# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false, reportRedeclaration=false, reportAssignmentType=false
from django.http import HttpResponse

class ExportExcelWorkbookGenerator(object):
    """
    Generates a multi-tab Excel Workbook from live DB data,
    matching the original Balance.xlsx format, styles, and formulas,
    with an added Expenses tab.
    """

    def get(self, request):
        return self.post(request)

    def post(self, request):
        from core.reports.excel_generator import generate_excel
        from datetime import date

        buf = generate_excel()
        filename = f"Balance_Tracker_{date.today().strftime('%Y%m%d')}.xlsx"
        response = HttpResponse(
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
