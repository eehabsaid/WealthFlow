"""Backward-compatibility shim: this file was split into
documentation_run_views.py (Capture/Generate) and
documentation_control_views.py (Cancel/OpenFolder) to stay under the
200-line-per-file limit. Re-exported here so the existing import path
(core.views.settings.documentation.documentation_action_views) keeps
working unchanged."""

from core.views.settings.documentation.documentation_run_views import (
    CaptureScreenshotsView,
    GenerateDocumentsView,
)
from core.views.settings.documentation.documentation_control_views import (
    CancelDocumentationView,
    OpenFolderView,
)

__all__ = [
    "CaptureScreenshotsView",
    "GenerateDocumentsView",
    "CancelDocumentationView",
    "OpenFolderView",
]
