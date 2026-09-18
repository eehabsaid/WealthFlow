"""
Pre-Promotion Benchmark views (AI Platform).

Split out of the former monolithic ai_platform_views.py (200-line rule).
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import AIBenchmarkReport
from core.services.ai.benchmark_engine import AIBenchmarkEngine
from core.services.ai.model_manager import AIModelManager
from core.views.ai_platform_views.auth import _api_auth_required


@method_decorator(csrf_exempt, name="dispatch")
class AIPlatformBenchmarkView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        reports = AIBenchmarkReport.objects.all().select_related("model_version")[:20]
        return JsonResponse({"benchmark_reports": [r.to_dict() for r in reports]})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        active = AIModelManager.get_active_model_version()
        report = AIBenchmarkEngine.evaluate_model_version(candidate_version=active, active_version=active)
        return JsonResponse({"ok": True, "benchmark_report": report.to_dict()})
