import os

# Base paths
DOC_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))


def _host_dirs():
    """(project root, docs folder) of the host Django project: the settings decide, so the Settings page, the capture engine and
    the generated documents all use ONE folder. AI_DOCS_DIR overrides it; outside Django the parent of the ai/ folder is used."""
    try:
        from django.conf import settings
        root = str(getattr(settings, "BASE_DIR", "") or "")
        docs = str(getattr(settings, "AI_DOCS_DIR", "") or "")
    except Exception:
        root = docs = ""
    root = root or os.path.dirname(os.path.dirname(DOC_ENGINE_DIR))
    return root, docs or os.path.join(root, "docs")


BASE_DIR, DOCS_DIR = _host_dirs()
GENERATED_DIR = os.path.join(DOCS_DIR, "generated")
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots")
TEMPLATES_DIR = os.path.join(DOC_ENGINE_DIR, "templates")

LATEST_SCREENSHOTS_DIR = os.path.join(SCREENSHOTS_DIR, "latest")
RUNTIME_DIR = os.path.join(GENERATED_DIR, "runtime")

# File locations
MANIFEST_FILE = os.path.join(RUNTIME_DIR, "manifest.json")
METADATA_FILE = os.path.join(RUNTIME_DIR, "capture_metadata.json")
STATUS_FILE = os.path.join(RUNTIME_DIR, "status.json")
CANCEL_FILE = os.path.join(RUNTIME_DIR, ".cancel_capture")
CONTENT_FILE = os.path.join(DOC_ENGINE_DIR, "content", "page_descriptions.json")

# Generation settings
DEFAULT_LANGUAGE = "en"
DEFAULT_THEME = "dark"
DEFAULT_DEVICE = "desktop"
SUPPORTED_FORMATS = ["markdown", "html", "pdf", "docx"]

# Image settings
IMAGE_MAX_WIDTH_PERCENT = 100
IMAGE_DOCX_WIDTH_INCHES = 6.0

def _resolve_playwright_backend():
    try:
        from django.conf import settings
        if hasattr(settings, 'PLAYWRIGHT_BACKEND'):
            return settings.PLAYWRIGHT_BACKEND.lower()
    except Exception:
        pass
    return os.environ.get("PLAYWRIGHT_BACKEND", "python").lower()

PLAYWRIGHT_BACKEND = _resolve_playwright_backend()





