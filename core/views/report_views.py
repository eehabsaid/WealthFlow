import os
import json as _json
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth import get_user_model

# Import delegators from core/reports
from core.reports.report_generators import (
    ExportExcelWorkbookGenerator,
    GenerateReportGenerator,
    FixedAssetPdfReportGenerator,
    FixedAssetExcelReportGenerator,
)

User = get_user_model()

@method_decorator(csrf_exempt, name="dispatch")
class ExportExcelWorkbookView(View):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        return ExportExcelWorkbookGenerator().post(request)


@login_required
def export_excel(request):
    return ExportExcelWorkbookGenerator().post(request)


@method_decorator(csrf_exempt, name="dispatch")
class GenerateReportView(View):
    def post(self, request):
        return GenerateReportGenerator().post(request)


@method_decorator(csrf_exempt, name="dispatch")
class SalaryReportView(View):
    def get(self, request):
        from core.reports.report_generators import SalaryReportView as SalaryReportGeneratorView
        return SalaryReportGeneratorView().get(request)

    def post(self, request):
        from core.reports.report_generators import SalaryReportView as SalaryReportGeneratorView
        return SalaryReportGeneratorView().post(request)


@method_decorator(csrf_exempt, name="dispatch")
class BalanceReportView(View):
    def get(self, request):
        from core.reports.report_generators import BalanceReportView as BalanceReportGeneratorView
        return BalanceReportGeneratorView().get(request)


@method_decorator(csrf_exempt, name="dispatch")
class CertificateReportView(View):
    def get(self, request):
        from core.reports.report_generators import CertificateReportView as CertificateReportGeneratorView
        return CertificateReportGeneratorView().get(request)


class FixedAssetPdfReportView(View):
    def get(self, request):
        return FixedAssetPdfReportGenerator().get(request)


@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetExcelReportView(View):
    def get(self, request):
        return FixedAssetExcelReportGenerator().get(request)