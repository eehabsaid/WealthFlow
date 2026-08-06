"""
AI Platform & Model Lifecycle Views.

Endpoints for Knowledge Base management, Autonomous Scans, Dataset Validation,
Model Version Control, Pluggable Training Triggers, and Pre-Promotion Benchmarks.
"""

import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.services.ai.knowledge_engine import AIKnowledgeEngine
from core.services.ai.autonomous_learning_engine import AIAutonomousLearningEngine
from core.services.ai.dataset_engine import AIDatasetEngine
from core.services.ai.model_manager import AIModelManager
from core.services.ai.benchmark_engine import AIBenchmarkEngine
from core.services.ai.training_backends import get_available_training_backends
from core.models import AIBenchmarkReport


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


@method_decorator(csrf_exempt, name="dispatch")
class AIPlatformKnowledgeView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        category = request.GET.get("category")
        entries = AIKnowledgeEngine.get_active_knowledge_entries(category=category)
        return JsonResponse({"entries": [e.to_dict() for e in entries]})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        action = str(body.get("action", "scan")).strip().lower()
        if action == "scan":
            res = AIAutonomousLearningEngine.scan_and_learn_application_evolution()
            return JsonResponse(res)

        key = str(body.get("key", "")).strip()
        title = str(body.get("title", "")).strip()
        content = str(body.get("content", "")).strip()
        category = str(body.get("category", "business_rule")).strip()

        if not key or not title or not content:
            return JsonResponse({"error": "Key, title, and content are required"}, status=400)

        entry = AIKnowledgeEngine.record_knowledge_entry(
            key=key,
            title=title,
            content=content,
            category=category,
            source="user_manual",
        )
        return JsonResponse({"entry": entry.to_dict()}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class AIPlatformDatasetView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        stats = AIDatasetEngine.validate_dataset()
        return JsonResponse({"dataset_stats": stats})

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        res = AIDatasetEngine.generate_sft_datasets()
        return JsonResponse(res)


@method_decorator(csrf_exempt, name="dispatch")
class AIPlatformModelView(View):
    def get(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        models = AIModelManager.get_all_model_versions()
        backends = get_available_training_backends()
        return JsonResponse(
            {
                "active_model": AIModelManager.get_active_model_version().to_dict(),
                "model_versions": [m.to_dict() for m in models],
                "available_backends": backends,
            }
        )

    def post(self, request):
        auth_error = _api_auth_required(request)
        if auth_error:
            return auth_error

        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}

        action = str(body.get("action", "fine_tune")).strip().lower()

        if action == "promote":
            version_name = str(body.get("version_name", "")).strip()
            promoted = AIModelManager.promote_model_version(version_name)
            if not promoted:
                return JsonResponse({"error": "Model version not found"}, status=404)
            return JsonResponse({"ok": True, "active_model": promoted.to_dict()})

        base_model = str(body.get("base_model", "llama3:latest")).strip()
        backend_name = str(body.get("backend_name", "ollama")).strip()

        res = AIModelManager.trigger_fine_tuning(base_model=base_model, backend_name=backend_name)
        return JsonResponse(res)


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
