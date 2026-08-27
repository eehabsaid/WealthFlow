# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py."""


import json
import tempfile
import os
from datetime import datetime
from django.http import JsonResponse, FileResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.core.management import call_command

from core.views.auth_views import AdminRequiredMixin

# ══════════════════════════════════════════════════════════════
# BACKUP & RESTORE VIEWS
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name="dispatch")
class BackupCreateView(AdminRequiredMixin, View):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        download = request.GET.get("download", "false").lower() == "true"
        if download:
            # Create backup in temporary directory
            temp_dir = tempfile.mkdtemp()
            filename = f"wealthflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wfbackup"
            filepath = os.path.join(temp_dir, filename)
            try:
                call_command("backup_data", output=temp_dir, filename=filename)
                # Return file for download
                response = FileResponse(open(filepath, "rb"), content_type="application/zip")
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
        else:
            # Create backup in default backups directory on the server
            backups_dir = os.path.join(settings.BASE_DIR, "backups")
            os.makedirs(backups_dir, exist_ok=True)
            filename = f"wealthflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wfbackup"
            try:
                call_command("backup_data", output=backups_dir, filename=filename)
                return JsonResponse({"success": True, "filename": filename})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class BackupListView(AdminRequiredMixin, View):
    def get(self, request):
        backups_dir = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        files = []
        for filename in os.listdir(backups_dir):
            if filename.endswith(".wfbackup"):
                filepath = os.path.join(backups_dir, filename)
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        # Sort files: latest first
        files.sort(key=lambda x: x["created_at"], reverse=True)
        return JsonResponse({"backups": files})

@method_decorator(csrf_exempt, name="dispatch")
class BackupDeleteView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            filename = data.get("filename")
            if not filename or ".." in filename or "/" in filename or "\\" in filename:
                return JsonResponse({"error": "Invalid filename"}, status=400)

            backups_dir = os.path.join(settings.BASE_DIR, "backups")
            filepath = os.path.join(backups_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"error": "File not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class BackupRestoreView(AdminRequiredMixin, View):
    def post(self, request):
        overwrite = request.GET.get("overwrite", "false").lower() == "true"

        # Check if it's an uploaded file
        if "file" in request.FILES:
            uploaded_file = request.FILES["file"]
            # Save it temporarily
            temp_dir = tempfile.mkdtemp()
            filepath = os.path.join(temp_dir, uploaded_file.name)
            with open(filepath, "wb") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            try:
                # Run restore command
                call_command("restore_data", filepath, overwrite=overwrite)
                return JsonResponse({"success": True})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
            finally:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
        else:
            # Server-side file restore
            try:
                data = json.loads(request.body)
                filename = data.get("filename")
                if not filename or ".." in filename or "/" in filename or "\\" in filename:
                    return JsonResponse({"error": "Invalid filename"}, status=400)

                backups_dir = os.path.join(settings.BASE_DIR, "backups")
                filepath = os.path.join(backups_dir, filename)
                if not os.path.exists(filepath):
                    return JsonResponse({"error": "File not found"}, status=404)

                call_command("restore_data", filepath, overwrite=overwrite)
                return JsonResponse({"success": True})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
