from django.http import JsonResponse
from django.views import View
from core.views.auth_views import PermissionRequiredMixin
from core.views.settings.documentation.documentation_constants import STATUS_FILE, read_json_file

from ai.doc_engine.device_inventory import load_inventory, validate_inventory


class ValidateCaptureView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"
    def get(self, request):
        from ai.doc_engine.services.playwright_validator import PlaywrightValidator
        res = PlaywrightValidator().validate_capture_environment()
        if not res["valid"]:
            return JsonResponse({"valid": False, "errors": res["errors"]})
        return JsonResponse({"valid": True})

class ValidateGenerationView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"
    def get(self, request):
        from ai.doc_engine.services.playwright_validator import PlaywrightValidator
        res = PlaywrightValidator().validate_generation_environment()
        if not res["valid"]:
            return JsonResponse({"valid": False, "errors": res["errors"]})
        return JsonResponse({"valid": True})


class DocumentationDevicesView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"
    def get(self, request):
        is_valid, err_msg = validate_inventory()
        if not is_valid:
            return JsonResponse({"error": f"Device inventory validation failed: {err_msg}"}, status=500)
        inventory = load_inventory()
        return JsonResponse(inventory)

class DocumentationStatusView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"
    def get(self, request):
        status = read_json_file(STATUS_FILE, {})
        return JsonResponse(status)

class DocumentationHistoryView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"
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
