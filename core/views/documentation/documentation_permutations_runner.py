import os
import sys
import time
import subprocess
from django.conf import settings
from core.views.documentation.documentation_constants import (
    BASE_DIR,
    DOCS_DIR,
    RUNTIME_DIR,
    STATUS_FILE,
    CANCEL_FILE,
    read_json_file,
    write_json_file,
)


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
                        pid_file = os.path.join(RUNTIME_DIR, "capture.pid")
                        proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
                        os.makedirs(RUNTIME_DIR, exist_ok=True)
                        with open(pid_file, "w", encoding="utf-8") as pf:
                            pf.write(str(proc.pid))

                        while proc.poll() is None:
                            if os.path.exists(CANCEL_FILE):
                                log_file.write("\n[System] Cancel requested. Terminating subprocess.\n")
                                try:
                                    if os.name == 'nt':
                                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    else:
                                        proc.kill()
                                except Exception:
                                    pass
                                break
                            time.sleep(0.2)

                        if os.path.exists(pid_file):
                            try:
                                os.remove(pid_file)
                            except Exception:
                                pass

                        if os.path.exists(CANCEL_FILE):
                            break
                        elif proc.returncode != 0:
                            has_fatal_error = True
                            break
                        else:
                            if mode == "BOTH":
                                log_file.write("\n[System] Running Document Generator...\n")
                                log_file.flush()
                                doc_cmd = [python_exe, "-c", "import sys, os; sys.path.insert(0, os.path.abspath('.')); from doc_engine.document_generator import DocumentationGenerator; DocumentationGenerator().generate_all('all')"]
                                doc_proc = subprocess.Popen(doc_cmd, cwd=BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT)
                                with open(pid_file, "w", encoding="utf-8") as pf:
                                    pf.write(str(doc_proc.pid))
                                while doc_proc.poll() is None:
                                    if os.path.exists(CANCEL_FILE):
                                        try:
                                            if os.name == 'nt':
                                                subprocess.run(["taskkill", "/F", "/T", "/PID", str(doc_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                            else:
                                                doc_proc.kill()
                                        except Exception:
                                            pass
                                        break
                                    time.sleep(0.2)

                                if os.path.exists(pid_file):
                                    try:
                                        os.remove(pid_file)
                                    except Exception:
                                        pass

                                if os.path.exists(CANCEL_FILE):
                                    break
                                elif doc_proc.returncode != 0:
                                    has_fatal_error = True
                                    log_file.write("\n[System] Document Generator failed.\n")
                                    break
                    except Exception as e:
                        log_file.write(f"\n[System] Exception occurred: {str(e)}\n")
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
