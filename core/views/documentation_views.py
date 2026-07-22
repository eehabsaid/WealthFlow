import os
import sys
import json
import threading
import subprocess
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
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots", "latest")
RUNTIME_DIR = os.path.join(GENERATED_DIR, "runtime")
HISTORY_FILE = os.path.join(GENERATED_DIR, "history.json")
STATUS_FILE = os.path.join(RUNTIME_DIR, "status.json")
CANCEL_FILE = os.path.join(RUNTIME_DIR, ".cancel_capture")

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
def run_documentation_generation_only(execution_id, doc_type="all"):
    from django.utils.timezone import now
    from core.models import DocumentationExecution
    
    execution = DocumentationExecution.objects.get(id=execution_id)
    
    logs_dir = os.path.join(DOCS_DIR, "generated", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = f"{execution.started_at.strftime('%Y-%m-%d_%H-%M-%S')}_{execution.id}.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    python_exe = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable
    
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("\\n[System] Running Document Generator...\\n")
        log_file.flush()
        doc_cmd = [python_exe, "-c", f"import sys, os; sys.path.insert(0, os.path.abspath('.')); from doc_engine.document_generator import DocumentationGenerator; DocumentationGenerator().generate_all('{doc_type}')"]
        
        has_fatal_error = False
        try:
            doc_result = subprocess.run(doc_cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
            if doc_result.returncode != 0:
                has_fatal_error = True
                log_file.write("\\n[System] Document Generator failed.\\n")
        except Exception as e:
            log_file.write(f"\\n[System] Exception occurred: {str(e)}\\n")
            has_fatal_error = True
            
    execution.finished_at = now()
    
    status = read_json_file(STATUS_FILE, {})
    from core.models.documentation import DocumentationExecutionStatus
    
    if os.path.exists(CANCEL_FILE):
        execution.status = DocumentationExecutionStatus.CANCELLED
        status["status"] = "CANCELLED"
        os.remove(CANCEL_FILE)
    elif has_fatal_error:
        execution.status = DocumentationExecutionStatus.FAILED
        status["status"] = "FAILED"
    else:
        execution.status = DocumentationExecutionStatus.COMPLETED
        status["status"] = "COMPLETED"
        if doc_type == "all":
            execution.files_generated = ["User Guide", "Administrator Guide", "Technical Guide"]
        elif doc_type == "user":
            execution.files_generated = ["User Guide"]
        elif doc_type == "admin":
            execution.files_generated = ["Administrator Guide"]
        elif doc_type == "technical":
            execution.files_generated = ["Technical Guide"]
        else:
            execution.files_generated = [doc_type.capitalize() + " Guide"]
        
    execution.save()
    write_json_file(STATUS_FILE, status)

def run_documentation_permutations(languages, themes, devices, execution_id, mode="BOTH"):
    from django.utils.timezone import now
    from core.models import DocumentationExecution
    
    execution = DocumentationExecution.objects.get(id=execution_id)
    
    logs_dir = os.path.join(DOCS_DIR, "generated", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = f"{execution.started_at.strftime('%Y-%m-%d_%H-%M-%S')}_{execution.id}.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    # Use the venv Python to ensure the correct environment
    python_exe = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable  # fallback to current Python
    
    with open(log_path, "a", encoding="utf-8") as log_file:
        has_fatal_error = False
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
                    
                    # device is now a device ID (e.g. "current", "iPhone 13", "1366x768")
                    # Only pass --device if it's not "current" (current resolution needs no emulation)
                    cmd = [python_exe, "scripts/generate_docs.py", "--lang", lang, "--theme", theme]
                    if device and device != "current":
                        cmd.extend(["--device", device])
                    
                    log_file.write(f"\n[System] Executing: {' '.join(cmd)}\n")
                    log_file.flush()
                    
                    try:
                        result = subprocess.run(cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
                        if os.path.exists(CANCEL_FILE):
                            break
                        elif result.returncode != 0:
                            has_fatal_error = True
                            break
                        else:
                            if mode == "BOTH":
                                # Run the document generator backend now that manifest is written
                                log_file.write("\\n[System] Running Document Generator...\\n")
                                log_file.flush()
                                doc_cmd = [python_exe, "-c", "import sys, os; sys.path.insert(0, os.path.abspath('.')); from doc_engine.document_generator import DocumentationGenerator; DocumentationGenerator().generate_all('all')"]
                                doc_result = subprocess.run(doc_cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
                                if doc_result.returncode != 0:
                                    has_fatal_error = True
                                    log_file.write("\\n[System] Document Generator failed.\\n")
                                    break
                    except Exception as e:
                        log_file.write(f"\\n[System] Exception occurred: {str(e)}\\n")
                        has_fatal_error = True
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
    elif execution.failed_pages > 0 or has_fatal_error:
        execution.status = DocumentationExecutionStatus.FAILED
        status["status"] = "FAILED"
    else:
        execution.status = DocumentationExecutionStatus.COMPLETED
        status["status"] = "COMPLETED"
        if mode == "BOTH":
            summary_path = os.path.join(DOCS_DIR, "generated", "latest", "generation_summary.json")
            if os.path.exists(summary_path):
                summary = read_json_file(summary_path, {})
                execution.pages = summary.get("pages_generated", 0)
                execution.warnings = summary.get("warnings", [])
                execution.errors = summary.get("errors", [])
                execution.missing_content_count = summary.get("missing_content_count", 0)
            execution.files_generated = ["User Guide", "Administrator Guide", "Technical Guide"]
            
        try:
            git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, text=True).strip()
        except Exception:
            git_hash = "Unknown"
        execution.git_commit_hash = git_hash
        execution.app_version = getattr(settings, "VERSION", "1.0.0")
        execution.engine_version = "2.0.0"
        
    execution.save()
    write_json_file(STATUS_FILE, status)


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

@method_decorator(csrf_exempt, name="dispatch")
class CaptureScreenshotsView(AdminRequiredMixin, View):
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
                except:
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
class GenerateDocumentsView(AdminRequiredMixin, View):
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
