import os
import json
import threading
import subprocess
import time
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.views.auth_views import AdminRequiredMixin

# Base directory for the Django project
BASE_DIR = settings.BASE_DIR
DOCS_DIR = os.path.join(BASE_DIR, "docs")
GENERATED_DIR = os.path.join(DOCS_DIR, "generated")
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots")
HISTORY_FILE = os.path.join(GENERATED_DIR, "history.json")
STATUS_FILE = os.path.join(GENERATED_DIR, "capture_status.json")
CANCEL_FILE = os.path.join(GENERATED_DIR, "cancel.flag")

from doc_engine.device_inventory import load_inventory, validate_inventory

def read_json_file(filepath, default_value):
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_value

def write_json_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# Background worker
def run_documentation_permutations(languages, themes, devices, execution_id):
    from django.utils.timezone import now
    from core.models import DocumentationExecution
    
    execution = DocumentationExecution.objects.get(id=execution_id)
    
    logs_dir = os.path.join(DOCS_DIR, "generated", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = f"{execution.started_at.strftime('%Y-%m-%d_%H-%M-%S')}_{execution.id}.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    with open(log_path, "a", encoding="utf-8") as log_file:
        for lang in languages:
            for theme in themes:
                for device in devices:
                    if os.path.exists(CANCEL_FILE):
                        log_file.write("\n[System] Cancel flag detected. Stopping permutations.\n")
                        break
                    
                    execution.language = lang
                    execution.theme = theme
                    execution.device_type = device
                    execution.save(update_fields=['language', 'theme', 'device_type'])
                    
                    cmd = ["python", "scripts/generate_docs.py", "--lang", lang, "--theme", theme]
                    if device != "Desktop":
                        cmd.extend(["--device", device])
                    
                    log_file.write(f"\n[System] Executing: {' '.join(cmd)}\n")
                    log_file.flush()
                    
                    try:
                        result = subprocess.run(cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
                        if os.path.exists(CANCEL_FILE):
                            break
                        elif result.returncode != 0:
                            break
                    except Exception as e:
                        log_file.write(f"\n[System] Exception occurred: {str(e)}\n")
                        break
    
    execution.finished_at = now()
    
    # Read status to get final screenshots count and failed pages
    status = read_json_file(STATUS_FILE, {})
    execution.screenshots_count = status.get("screenshots_count", 0)
    execution.failed_pages = len(status.get("failed_pages", []))
    
    from core.models.documentation import DocumentationExecutionStatus
    
    if os.path.exists(CANCEL_FILE):
        execution.status = DocumentationExecutionStatus.CANCELLED
        status["status"] = "CANCELLED"
        os.remove(CANCEL_FILE)
    elif execution.failed_pages > 0:
        execution.status = DocumentationExecutionStatus.FAILED
        status["status"] = "FAILED"
    else:
        execution.status = DocumentationExecutionStatus.COMPLETED
        status["status"] = "COMPLETED"
        
    execution.save()
    write_json_file(STATUS_FILE, status)


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
                "language": exec_obj.language,
                "theme": exec_obj.theme,
                "device": exec_obj.device_type,
                "status": exec_obj.status,
                "screenshots": exec_obj.screenshots_count,
                "failed": exec_obj.failed_pages,
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
            
            status = read_json_file(STATUS_FILE, {})
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

@method_decorator(csrf_exempt, name="dispatch")
class CancelDocumentationView(AdminRequiredMixin, View):
    def post(self, request):
        os.makedirs(os.path.dirname(CANCEL_FILE), exist_ok=True)
        with open(CANCEL_FILE, "w") as f:
            f.write("cancel")
        return JsonResponse({"success": True})

@method_decorator(csrf_exempt, name="dispatch")
class OpenFolderView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            target = data.get("target")
            
            target_path = None
            if target == "screenshots":
                target_path = SCREENSHOTS_DIR
                os.makedirs(target_path, exist_ok=True)
            elif target == "generated":
                target_path = GENERATED_DIR
                os.makedirs(target_path, exist_ok=True)
            elif target == "readme":
                target_path = os.path.join(BASE_DIR, "doc_engine", "README.md")
            
            if target_path and os.path.exists(target_path):
                if os.name == 'nt':
                    os.startfile(target_path)
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"error": "Path not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
