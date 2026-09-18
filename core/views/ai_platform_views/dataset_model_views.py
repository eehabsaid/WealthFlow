"""
Dataset Validation and Model Version Control views (AI Platform).

Split out of the former monolithic ai_platform_views.py (200-line rule).
"""

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import AppSettings
from core.services.ai.ai_defaults import DEFAULT_OLLAMA_MODEL
from core.services.ai.dataset_engine import AIDatasetEngine
from core.services.ai.model_manager import AIModelManager
from core.services.ai.training_backends import get_available_training_backends
from core.views.ai_platform_views.auth import _api_auth_required


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
                # The Ollama tag actually used by live chat right now — a model
                # the user has already confirmed is pulled and working, used as
                # the frontend's default base-model suggestion instead of a
                # hardcoded tag that may not exist on this machine.
                "live_chat_model": AppSettings.get("ai_model", DEFAULT_OLLAMA_MODEL),
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

        base_model = str(body.get("base_model", "")).strip() or None
        backend_name = str(body.get("backend_name", "ollama")).strip()

        res = AIModelManager.trigger_fine_tuning(base_model=base_model, backend_name=backend_name)
        return JsonResponse(res)
