import os
import json
import threading
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.views.auth_views import AdminRequiredMixin
from core.views.documentation.documentation_constants import STATUS_FILE, CANCEL_FILE, read_json_file, write_json_file
from core.views.documentation.documentation_permutations_runner import run_documentation_permutations

from doc_engine.device_inventory import load_inventory, validate_inventory


@method_decorator(csrf_exempt, name="dispatch")
class ValidateCaptureView(AdminRequiredMixin, View):
    def get(self, request):
        from doc_engine.services.playwright_validator import PlaywrightValidator
        res = PlaywrightValidator().validate_capture_environment()
        if not res["valid"]:
            return JsonResponse({"valid": False, "errors": res["errors"]})
        return JsonResponse({"valid": True})

@method_decorator(csrf_exempt, name="dispatch")
class ValidateGenerationView(AdminRequiredMixin, View):
    def get(self, request):
        from doc_engine.services.playwright_validator import PlaywrightValidator
        res = PlaywrightValidator().validate_generation_environment()
        if not res["valid"]:
            return JsonResponse({"valid": False, "errors": res["errors"]})
        return JsonResponse({"valid": True})



@method_decorator(csrf_exempt, name="dispatch")
class DocumentationDevicesView(AdminRequiredMixin, View):
    def get(self, request):
        is_valid, err_msg = validate_inventory()
        if not is_valid:
            return JsonResponse({"error": f"Device inventory validation failed: {err_msg}"}, status=500)
        inventory = load_inventory()
        return JsonResponse(inventory)

class DocumentationStatusView(AdminRequiredMixin, View):
    def get(self, request):
        status = read_json_file(STATUS_FILE, {})
        return JsonResponse(status)

@method_decorator(csrf_exempt, name="dispatch")
class DocumentationHistoryView(AdminRequiredMixin, View):
    def get(self, request):
        from core.models import DocumentationExecution
        from django.utils.timezone import localtime
        
        history_qs = DocumentationExecution.objects.all().order_by('-started_at')[:20]
        history = []
        for exec_obj in history_qs:
            if exec_obj.finished_at:
                elapsed = int((exec_obj.finished_at - exec_obj.started_at).total_seconds())
                duration_str = f"{elapsed}s"
            else:
                duration_str = "-"
                
            history.append({
                "date": localtime(exec_obj.started_at).strftime("%Y-%m-%d %H:%M:%S"),
                "duration": duration_str,
                "type": exec_obj.execution_type,
                "language": exec_obj.language,
                "theme": exec_obj.theme,
                "device": exec_obj.device_type,
                "status": exec_obj.status,
                "screenshots": exec_obj.screenshots_count,
                "failed": exec_obj.failed_pages,
                "files_generated": exec_obj.files_generated,
                "created_by": exec_obj.created_by.username if exec_obj.created_by else "System"
            })
        return JsonResponse({"history": history})

@method_decorator(csrf_exempt, name="dispatch")
class GenerateDocumentationView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            lang_opt = data.get("language", "en")
            theme_opt = data.get("theme", "dark")
            category_opt = data.get("device_category", "Desktop")
            device_opt = data.get("device_type", "Desktop")
            
            # Remove any lingering cancel.flag
            if os.path.exists(CANCEL_FILE):
                os.remove(CANCEL_FILE)
            
            from core.models import DocumentationExecution
            from core.models.documentation import DocumentationExecutionStatus
            
            if DocumentationExecution.objects.filter(status=DocumentationExecutionStatus.RUNNING).exists():
                return JsonResponse({"error": "Documentation generation already running."}, status=400)
            
            # Resolve permutations
            from core.models import AppSettings
            
            languages = [lang_opt]
            if lang_opt == "ALL":
                supported_langs_str = AppSettings.get("available_languages", "[]")
                try:
                    langs = json.loads(supported_langs_str)
                    languages = [l.get("code") for l in langs if l.get("code")]
                except:
                    languages = ["en"]
                if not languages:
                    languages = ["en"]
                
            themes = [theme_opt]
            if theme_opt == "ALL":
                themes = ["dark", "light"]
                
            devices = [device_opt]
            if category_opt == "ALL":
                is_valid, err_msg = validate_inventory()
                if not is_valid:
                    return JsonResponse({"error": f"Device inventory invalid: {err_msg}"}, status=500)
                
                inventory = load_inventory()
                categories = inventory.get("categories", {})
                
                devices = []
                for cat_name, items in categories.items():
                    for item in items:
                        if isinstance(item, dict) and item.get("enabled", True):
                            devices.append(item["id"])
                
                if not devices:
                    devices = ["current"]
                
            initial_status = {
                "status": "RUNNING",
                "page": "Starting...",
                "tab": "-",
                "language": languages[0],
                "theme": themes[0],
                "device": devices[0],
                "progress": 0,
                "total": 0,
                "elapsed_seconds": 0,
                "error": "",
                "failed_pages": []
            }
            write_json_file(STATUS_FILE, initial_status)
            
            new_execution = DocumentationExecution.objects.create(
                language=languages[0],
                theme=themes[0],
                device_category=category_opt,
                device_type=devices[0],
                status=DocumentationExecutionStatus.RUNNING,
                created_by=request.user if request.user.is_authenticated else None
            )
            
            # Start background thread
            thread = threading.Thread(target=run_documentation_permutations, args=(languages, themes, devices, new_execution.id))
            thread.daemon = True
            thread.start()
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
