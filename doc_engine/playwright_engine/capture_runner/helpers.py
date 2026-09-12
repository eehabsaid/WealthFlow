"""Module-level helpers for the Playwright capture engine: CDN fallback
routing, timestamped logging, and cancellation checks. Split out of the
original capture_runner.py monolith; see this package's __init__.py for
the sibling list and composition conventions."""
import os
import sys
import logging
from datetime import datetime

from playwright.sync_api import Page

from doc_engine.services.documentation_metadata_service import DocumentationMetadataService


logger = logging.getLogger(__name__)

# Configurable browser visibility mode:
# 1 = Environment-controlled mode (Default: headless unless WF_DOC_ENGINE_HEADED=1)
# 0 = Force old behavior (always headed/visible browser window, headless=False)
USE_ENV_HEADLESS_CONFIG = 0

# Local vendored copies of the app's external CDN dependencies
# (bootstrap.bundle.min.js, chart.umd.js, leaflet.js/css, bootstrap CSS/icons).
# Some server/CI/sandboxed network environments block or cannot reach
# cdn.jsdelivr.net, cdnjs.cloudflare.com, or unpkg.com (confirmed: this
# occurs in at least one real environment used to run this capture engine,
# manifesting as "bootstrap is not defined" / "Chart is not a constructor"
# and cascading into modal-open failures across many pages). Serving these
# exact, pinned-version files locally via request interception makes capture
# reliable regardless of the network's CDN reachability, without changing
# what the app itself serves to real users.
_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "vendor", "assets")

_CDN_LOCAL_MAP = {
    "bootstrap.bundle.min.js": "bootstrap.bundle.min.js",
    "bootstrap.min.css": "bootstrap.min.css",
    "bootstrap-icons.css": "bootstrap-icons.css",
    "bootstrap-icons.woff2": "fonts/bootstrap-icons.woff2",
    "bootstrap-icons.woff": "fonts/bootstrap-icons.woff",
    "chart.umd.min.js": "chart.umd.js",
    "chart.umd.js": "chart.umd.js",
    "leaflet.js": "leaflet.js",
    "leaflet.css": "leaflet.css",
}


def _install_cdn_fallback(page: Page) -> None:
    """Intercepts known CDN requests and serves a local vendored copy if the
    real network request would otherwise be blocked/unreachable. Falls back
    to the real network for anything not recognized, so this only changes
    behavior for the specific libraries known to sometimes fail here."""
    def handle_route(route):
        url = route.request.url
        for cdn_name, local_name in _CDN_LOCAL_MAP.items():
            if cdn_name in url:
                local_path = os.path.join(_VENDOR_DIR, local_name)
                if os.path.isfile(local_path):
                    route.fulfill(path=local_path)
                    return
        route.continue_()

    page.route("https://cdn.jsdelivr.net/**", handle_route)
    page.route("https://cdnjs.cloudflare.com/**", handle_route)
    page.route("https://unpkg.com/**", handle_route)


def log(msg: str) -> None:
    """Logs message with format matching capture_pages.js time format."""
    now_str = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{now_str}] {msg}")
    except UnicodeEncodeError:
        safe_msg = msg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
        print(f"[{now_str}] {safe_msg}")


def check_cancelled_and_exit(manifest_service: DocumentationMetadataService) -> None:
    if manifest_service.check_cancelled():
        print("\n[!] Cancellation requested. Stopping capture.")
        manifest_service.update_status('cancelled')
        sys.exit(0)
