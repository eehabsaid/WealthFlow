import os
import sys
import subprocess
from core.views.settings.documentation.documentation_constants import (
    BASE_DIR,
    DOCS_DIR,
    STATUS_FILE,
    CANCEL_FILE,
    read_json_file,
    write_json_file,
)


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
