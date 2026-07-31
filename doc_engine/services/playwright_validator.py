import os
import sys
import subprocess
from typing import Dict, Any
from doc_engine.config import SCREENSHOTS_DIR, GENERATED_DIR

def _ensure_venv_site_packages():
    try:
        from django.conf import settings
        if hasattr(settings, 'BASE_DIR'):
            venv_site = os.path.join(settings.BASE_DIR, 'venv', 'Lib', 'site-packages') if os.name == 'nt' else os.path.join(settings.BASE_DIR, 'venv', 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
            if os.path.exists(venv_site) and venv_site not in sys.path:
                sys.path.insert(0, venv_site)
    except Exception:
        pass

_ensure_venv_site_packages()

class PlaywrightValidator:
    """
    Dedicated validator for Python Playwright environment readiness.
    Views and CLI commands delegate environment checks to this class.
    """
    def __init__(self, backend: str = None):
        pass

    def _get_python_exe(self) -> str:
        python_exe = None
        try:
            from django.conf import settings
            if hasattr(settings, 'BASE_DIR'):
                venv_python = os.path.join(settings.BASE_DIR, 'venv', 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(settings.BASE_DIR, 'venv', 'bin', 'python')
                if os.path.exists(venv_python):
                    python_exe = venv_python
        except Exception:
            pass

        if not python_exe:
            prefix_python = os.path.join(sys.prefix, "Scripts", "python.exe") if os.name == 'nt' else os.path.join(sys.prefix, "bin", "python")
            if os.path.exists(prefix_python):
                python_exe = prefix_python
            else:
                python_exe = sys.executable

        return python_exe

    def validate_capture_environment(self) -> Dict[str, Any]:
        """Validates environment readiness for running Python screenshot capture."""
        errors = []
        python_exe = self._get_python_exe()

        try:
            res = subprocess.run([python_exe, "-c", "import playwright"], capture_output=True)
            if res.returncode != 0:
                errors.append("Playwright Python package is not installed in Python environment.")
        except Exception:
            errors.append("Playwright Python package is not installed in Python environment.")

        try:
            res = subprocess.run([python_exe, "-c", "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.executable_path; p.stop()"], capture_output=True)
            if res.returncode != 0:
                errors.append("Playwright Chromium browser binary is missing or not installed.")
        except Exception:
            errors.append("Playwright Chromium browser binary is missing or not installed.")

        try:
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            if not os.access(SCREENSHOTS_DIR, os.W_OK):
                errors.append("Screenshots directory is not writable.")
        except Exception:
            errors.append("Cannot create screenshots directory.")

        return {"valid": len(errors) == 0, "errors": errors}

    def validate_generation_environment(self) -> Dict[str, Any]:
        """Validates environment readiness for documentation document generation."""
        errors = []

        if not os.path.exists(SCREENSHOTS_DIR) or not os.listdir(SCREENSHOTS_DIR):
            errors.append("Screenshot folder is missing or contains no screenshots.")

        try:
            os.makedirs(GENERATED_DIR, exist_ok=True)
            if not os.access(GENERATED_DIR, os.W_OK):
                errors.append("Output directory is not writable.")
        except Exception:
            errors.append("Cannot create output directory.")

        _ensure_venv_site_packages()
        python_exe = self._get_python_exe()

        docx_ok = False
        try:
            __import__("docx")
            docx_ok = True
        except ImportError:
            try:
                res = subprocess.run([python_exe, "-c", "import docx"], capture_output=True)
                if res.returncode == 0:
                    docx_ok = True
            except Exception:
                pass

        if not docx_ok:
            errors.append("python-docx is not installed.")

        md_ok = False
        try:
            __import__("markdown")
            md_ok = True
        except ImportError:
            try:
                res = subprocess.run([python_exe, "-c", "import markdown"], capture_output=True)
                if res.returncode == 0:
                    md_ok = True
            except Exception:
                pass

        if not md_ok:
            errors.append("Markdown renderer is not available.")

        return {"valid": len(errors) == 0, "errors": errors}
