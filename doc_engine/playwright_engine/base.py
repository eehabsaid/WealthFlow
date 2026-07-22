import os
import subprocess
import logging

from abc import ABC, abstractmethod
from typing import Optional

from doc_engine.config import PLAYWRIGHT_BACKEND, NODE_PDF_SCRIPT, BASE_DIR

logger = logging.getLogger(__name__)

class PlaywrightBackend(ABC):
    """
    Abstract Strategy Interface for Playwright automation backends.
    Allows zero-cost switching between Python and legacy JavaScript backends.
    """

    @abstractmethod
    def capture(self, language: str = 'en', theme: str = 'dark', device: Optional[str] = None,
                host: str = '127.0.0.1', port: str = '8001') -> bool:
        """Executes full page screenshot capture workflow."""
        pass

    @abstractmethod
    def render_pdf(self, input_html_path: str, output_pdf_path: str) -> bool:
        """Renders HTML file into PDF format."""
        pass


class PythonPlaywrightBackend(PlaywrightBackend):
    """Native Python Playwright Backend implementation."""

    def capture(self, language: str = 'en', theme: str = 'dark', device: Optional[str] = None,
                host: str = '127.0.0.1', port: str = '8001') -> bool:
        from doc_engine.playwright_engine.capture_runner import run_python_capture
        return run_python_capture(
            host=host, port=port,
            username=os.environ.get('WF_USERNAME', 'eehab_said'),
            password=os.environ.get('WF_PASSWORD', 'Eehabdev1'),
            theme=theme, language=language, device=device
        )

    def render_pdf(self, input_html_path: str, output_pdf_path: str) -> bool:
        from doc_engine.playwright_engine.pdf_runner import run_python_pdf_render
        return run_python_pdf_render(input_html_path, output_pdf_path)


class JavaScriptPlaywrightBackend(PlaywrightBackend):
    """Legacy Node.js JavaScript Playwright Backend implementation."""

    def capture(self, language: str = 'en', theme: str = 'dark', device: Optional[str] = None,
                host: str = '127.0.0.1', port: str = '8001') -> bool:
        env = os.environ.copy()
        env['DOC_HOST'] = host
        env['DOC_PORT'] = port
        env['DOC_LANG'] = language
        env['DOC_THEME'] = theme
        if device:
            env['DOC_DEVICE'] = device
        else:
            env.pop('DOC_DEVICE', None)

        capture_script = os.path.join(BASE_DIR, 'doc_engine', 'capture_pages.js')
        proc = subprocess.run(['node', capture_script], env=env)
        return proc.returncode == 0

    def render_pdf(self, input_html_path: str, output_pdf_path: str) -> bool:
        if not os.path.exists(NODE_PDF_SCRIPT):
            logger.error(f"Cannot generate PDF, missing {NODE_PDF_SCRIPT}")
            return False
        try:
            cmd = ["node", NODE_PDF_SCRIPT, input_html_path, output_pdf_path]
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            logger.error(f"JS PDF generation failed: {e}")
            return False


def get_playwright_backend(name: Optional[str] = None) -> PlaywrightBackend:
    """
    Factory function retrieving the active PlaywrightBackend strategy.
    Respects priority: explicit parameter -> settings.PLAYWRIGHT_BACKEND -> env -> default ('python').
    """
    if not name:
        try:
            from django.conf import settings
            name = getattr(settings, 'PLAYWRIGHT_BACKEND', None)
        except Exception:
            name = None

    if not name:
        name = os.environ.get("PLAYWRIGHT_BACKEND", PLAYWRIGHT_BACKEND)

    backend_key = (name or "python").lower()

    if backend_key == "python":
        return PythonPlaywrightBackend()
    elif backend_key == "javascript" or backend_key == "js":
        return JavaScriptPlaywrightBackend()
    else:
        logger.warning(f"Unknown Playwright backend '{backend_key}'. Falling back to PythonPlaywrightBackend.")
        return PythonPlaywrightBackend()
