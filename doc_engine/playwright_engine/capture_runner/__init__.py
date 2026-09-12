"""Python Playwright capture engine, split into a package to stay under
the 200-line-per-file ceiling. Structural split only - no logic changes.

Siblings:
- helpers.py: module-level CDN fallback routing, timestamped log(), and
  check_cancelled_and_exit() - shared free functions, not part of the class.
- lifecycle.py: LifecycleMixin - construction and UI-readiness waits.
- capture.py: CaptureMixin - screenshot capture and modal-close/tab capture.
- asset_rows.py: AssetRowsMixin - per-row View/Edit modal capture.
- modals.py: ModalsMixin - tab-click helpers and generic modal capture.
- auth.py: AuthMixin - retry wrapper and login flow.
- discovery.py: DiscoveryMixin - live sidebar/tab discovery and merging.
- table_edits.py: TableEditsMixin - per-row table Edit-modal capture.
- dynamic_routes.py: DynamicRoutesMixin - runtime-discovered route injection.
- page_processing.py: PageProcessingMixin - per-page capture orchestration.
- run.py: RunMixin - top-level browser lifecycle and run orchestration.

PythonPlaywrightCaptureEngine below composes all mixins via multiple
inheritance so every method still shares a single `self` exactly as it did
in the original monolithic class. This __init__.py is the only place the
composed class and the module-level entry point are defined; sibling files
must never be imported for their own module-level API - always import from
this package root (`doc_engine.playwright_engine.capture_runner`).
"""
from typing import Optional

from .lifecycle import LifecycleMixin
from .capture import CaptureMixin
from .asset_rows import AssetRowsMixin
from .modals import ModalsMixin
from .auth import AuthMixin
from .discovery import DiscoveryMixin
from .table_edits import TableEditsMixin
from .dynamic_routes import DynamicRoutesMixin
from .page_processing import PageProcessingMixin
from .run import RunMixin


class PythonPlaywrightCaptureEngine(
    LifecycleMixin,
    CaptureMixin,
    AssetRowsMixin,
    ModalsMixin,
    AuthMixin,
    DiscoveryMixin,
    TableEditsMixin,
    DynamicRoutesMixin,
    PageProcessingMixin,
    RunMixin,
):
    """
    Thin, robust Playwright Python automation engine for screenshot generation.
    Receives configuration, inventory, and navigation context from Python services.
    """
    pass


def run_python_capture(host: str = '127.0.0.1', port: str = '8001',
                       username: str = 'eehab_said', password: str = 'Eehabdev1',
                       theme: str = 'dark', language: str = 'en', device: Optional[str] = None) -> bool:
    """Entry point function to invoke Python Playwright capture engine."""
    engine = PythonPlaywrightCaptureEngine(
        host=host, port=port, username=username, password=password,
        theme=theme, language=language, device=device
    )
    return engine.run()
