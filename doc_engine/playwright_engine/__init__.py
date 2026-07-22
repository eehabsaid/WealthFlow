"""
Playwright Python engine package.
Contains Playwright Strategy pattern interface, Python engine, and legacy JS proxy.
"""

from .base import PlaywrightBackend, PythonPlaywrightBackend, JavaScriptPlaywrightBackend, get_playwright_backend
from .capture_runner import run_python_capture
from .pdf_runner import run_python_pdf_render

__all__ = [
    "PlaywrightBackend",
    "PythonPlaywrightBackend",
    "JavaScriptPlaywrightBackend",
    "get_playwright_backend",
    "run_python_capture",
    "run_python_pdf_render"
]
