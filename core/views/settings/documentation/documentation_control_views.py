import os
import json
import subprocess
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.views.auth_views import PermissionRequiredMixin
from core.views.settings.documentation.documentation_constants import (
    BASE_DIR,
    DOCS_DIR,
    GENERATED_DIR,
    SCREENSHOTS_DIR,
    RUNTIME_DIR,
    STATUS_FILE,
    CANCEL_FILE,
    read_json_file,
    write_json_file,
)


@method_decorator(csrf_exempt, name="dispatch")
class CancelDocumentationView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"

    def post(self, request):
        from django.utils.timezone import now
        from core.models import DocumentationExecution
        from core.models.documentation import DocumentationExecutionStatus

        os.makedirs(os.path.dirname(CANCEL_FILE), exist_ok=True)
        with open(CANCEL_FILE, "w", encoding="utf-8") as f:
            f.write("cancel")

        status = read_json_file(STATUS_FILE, {})
        status["status"] = "CANCELLED"
        status["finished_at"] = now().isoformat()
        status["error"] = "Cancelled by user"
        write_json_file(STATUS_FILE, status)

        DocumentationExecution.objects.filter(
            status=DocumentationExecutionStatus.RUNNING
        ).update(status=DocumentationExecutionStatus.CANCELLED, finished_at=now())

        pid_file = os.path.join(RUNTIME_DIR, "capture.pid")
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r", encoding="utf-8") as pf:
                    pid = int(pf.read().strip())
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.kill(pid, 9)
            except Exception:
                pass
            try:
                os.remove(pid_file)
            except Exception:
                pass

        doc_server_pid = os.path.join(DOCS_DIR, "generated", "server.pid")
        if os.path.exists(doc_server_pid):
            try:
                with open(doc_server_pid, "r", encoding="utf-8") as pf:
                    spid = int(pf.read().strip())
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(spid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.kill(spid, 9)
            except Exception:
                pass
            try:
                os.remove(doc_server_pid)
            except Exception:
                pass

        return JsonResponse({"success": True, "status": "CANCELLED"})


@method_decorator(csrf_exempt, name="dispatch")
class OpenFolderView(PermissionRequiredMixin, View):
    required_key = "settings_documentation"

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
