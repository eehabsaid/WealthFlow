import os
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

class PlaywrightBackend(ABC):
    """
    Abstract Interface for Playwright automation backend.
    Enforces a thin, standardized contract for screenshot capture and PDF rendering.
    """

    @abstractmethod
    def capture(self, language: str = 'en', theme: str = 'dark', device: Optional[str] = None,
                host: str = '127.0.0.1', port: str = '8001',
                username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Executes full page screenshot capture workflow."""
        pass

    @abstractmethod
    def render_pdf(self, input_html_path: str, output_pdf_path: str) -> bool:
        """Renders HTML file into PDF format."""
        pass


class PythonPlaywrightBackend(PlaywrightBackend):
    """Native Python Playwright Backend implementation."""

    def capture(self, language: str = 'en', theme: str = 'dark', device: Optional[str] = None,
                host: str = '127.0.0.1', port: str = '8001',
                username: Optional[str] = None, password: Optional[str] = None) -> bool:
        from doc_engine.playwright_engine.capture_runner import run_python_capture

        resolved_username = username or os.environ.get('WF_USERNAME')
        resolved_password = password or os.environ.get('WF_PASSWORD')
        if not resolved_username or not resolved_password:
            raise RuntimeError(
                "No credentials provided for the documentation screenshot capture "
                "login. Pass --username/--password to scripts/generate_docs.py, or "
                "set the WF_USERNAME and WF_PASSWORD environment variables."
            )

        return run_python_capture(
            host=host, port=port,
            username=resolved_username,
            password=resolved_password,
            theme=theme, language=language, device=device
        )

    def render_pdf(self, input_html_path: str, output_pdf_path: str) -> bool:
        from doc_engine.playwright_engine.pdf_runner import run_python_pdf_render
        return run_python_pdf_render(input_html_path, output_pdf_path)


def get_playwright_backend(name: Optional[str] = None) -> PlaywrightBackend:
    """
    Factory function retrieving the active PlaywrightBackend instance.
    Returns PythonPlaywrightBackend for complete native Python execution.
    """
    return PythonPlaywrightBackend()
