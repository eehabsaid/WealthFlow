import os
import json
import threading
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.views.auth_views import PermissionRequiredMixin
from core.views.settings.documentation.documentation_constants import (
    STATUS_FILE,
    CANCEL_FILE,
    write_json_file,
)
from core.views.settings.documentation.documentation_runner import run_documentation_generation_only
from core.views.settings.documentation.documentation_permutations_runner import run_documentation_permutations
from doc_engine.device_inventory import load_inventory, validate_inventory


@method_decorator(csrf_exempt, name="dispatch")
class CaptureScreenshotsView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"

    def post(self, request):
        try:
            data = json.loads(request.body)
            lang_opt = data.get("language", "en")
            theme_opt = data.get("theme", "dark")
            category_opt = data.get("device_category", "Desktop")
            device_opt = data.get("device_type", "Desktop")

            if os.path.exists(CANCEL_FILE):
                os.remove(CANCEL_FILE)

            from core.models import DocumentationExecution
            from core.models.documentation import DocumentationExecutionStatus, DocumentationExecutionType

            if DocumentationExecution.objects.filter(status=DocumentationExecutionStatus.RUNNING).exists():
                return JsonResponse({"error": "Documentation process already running."}, status=400)

            from core.models import AppSettings
            languages = [lang_opt]
            if lang_opt == "ALL":
                try:
                    langs = json.loads(AppSettings.get("available_languages", "[]"))
                    languages = [l.get("code") for l in langs if l.get("code")]
                except Exception:
                    languages = ["en"]
                if not languages:
                    languages = ["en"]

            themes = [theme_opt]
            if theme_opt == "ALL":
                themes = ["dark", "light"]

            devices = [device_opt]
            if category_opt == "ALL":
                is_valid, _ = validate_inventory()
                if is_valid:
                    inventory = load_inventory()
                    devices = [item["id"] for items in inventory.get("categories", {}).values() for item in items if isinstance(item, dict) and item.get("enabled", True)]
                if not devices:
                    devices = ["current"]

            initial_status = {
                "status": "RUNNING", "page": "Starting...", "tab": "-", "language": languages[0], "theme": themes[0], "device": devices[0], "progress": 0, "total": 0, "elapsed_seconds": 0, "error": "", "failed_pages": []
            }
            write_json_file(STATUS_FILE, initial_status)

            new_execution = DocumentationExecution.objects.create(
                execution_type=DocumentationExecutionType.CAPTURE,
                language=languages[0], theme=themes[0], device_category=category_opt, device_type=devices[0],
                status=DocumentationExecutionStatus.RUNNING, created_by=request.user if request.user.is_authenticated else None
            )

            thread = threading.Thread(target=run_documentation_permutations, args=(languages, themes, devices, new_execution.id, "CAPTURE"))
            thread.daemon = True
            thread.start()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class GenerateDocumentsView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"

    def post(self, request):
        try:
            data = json.loads(request.body)
            doc_type = data.get("docs", "all")
            if os.path.exists(CANCEL_FILE):
                os.remove(CANCEL_FILE)

            from core.models import DocumentationExecution
            from core.models.documentation import DocumentationExecutionStatus, DocumentationExecutionType

            if DocumentationExecution.objects.filter(status=DocumentationExecutionStatus.RUNNING).exists():
                return JsonResponse({"error": "Documentation process already running."}, status=400)

            initial_status = {
                "status": "RUNNING", "page": "Generating Docs...", "tab": "-", "language": "N/A", "theme": "N/A", "device": "N/A", "progress": 0, "total": 0, "elapsed_seconds": 0, "error": "", "failed_pages": []
            }
            write_json_file(STATUS_FILE, initial_status)

            new_execution = DocumentationExecution.objects.create(
                execution_type=DocumentationExecutionType.GENERATION,
                language="N/A", theme="N/A", device_category="N/A", device_type="N/A",
                status=DocumentationExecutionStatus.RUNNING, created_by=request.user if request.user.is_authenticated else None
            )

            thread = threading.Thread(target=run_documentation_generation_only, args=(new_execution.id, doc_type))
            thread.daemon = True
            thread.start()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
