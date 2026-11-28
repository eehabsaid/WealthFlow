from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

# Import delegators from core/reports
from core.reports.report_generators import (
    ExportExcelWorkbookGenerator,
    GenerateReportGenerator,
    FixedAssetPdfReportGenerator,
    FixedAssetExcelReportGenerator,
)

User = get_user_model()

class ExportExcelWorkbookView(View):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        return ExportExcelWorkbookGenerator().post(request)

@login_required
def export_excel(request):
    return ExportExcelWorkbookGenerator().post(request)

class GenerateReportView(View):
    def post(self, request):
        return GenerateReportGenerator().post(request)

class SalaryReportView(View):
    def get(self, request):
        from core.reports.report_generators import SalaryReportView as SalaryReportGeneratorView
        return SalaryReportGeneratorView().get(request)

    def post(self, request):
        from core.reports.report_generators import SalaryReportView as SalaryReportGeneratorView
        return SalaryReportGeneratorView().post(request)

class BalanceReportView(View):
    def get(self, request):
        from core.reports.report_generators import BalanceReportView as BalanceReportGeneratorView
        return BalanceReportGeneratorView().get(request)

class CertificateReportView(View):
    def get(self, request):
        from core.reports.report_generators import CertificateReportView as CertificateReportGeneratorView
        return CertificateReportGeneratorView().get(request)

class FixedAssetPdfReportView(View):
    def get(self, request):
        return FixedAssetPdfReportGenerator().get(request)

class FixedAssetExcelReportView(View):
    def get(self, request):
        return FixedAssetExcelReportGenerator().get(request)

class IncomeReportView(View):
    def get(self, request):
        from core.reports.income_report_view import IncomeReportView as IncomeReportGeneratorView
        return IncomeReportGeneratorView().get(request)

class IncomeExportView(View):
    def get(self, request):
        from core.reports.income_report_view import IncomeExportView as IncomeExportGeneratorView
        return IncomeExportGeneratorView().get(request)