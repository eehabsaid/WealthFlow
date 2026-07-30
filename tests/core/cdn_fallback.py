"""
Shared CDN fallback for Playwright-driven automation (doc engine capture
runner and the E2E test suite both use this).

Some environments (CI runners, sandboxed containers, restricted networks)
block or cannot reliably reach cdn.jsdelivr.net, cdnjs.cloudflare.com, or
unpkg.com - the CDNs this app's templates load Bootstrap, Chart.js, and
Leaflet from. When that happens, the app's own JS throws real runtime
errors ("bootstrap is not defined", "Chart is not a constructor") and any
Bootstrap-dependent action (modals, toasts) hangs or fails outright.

This module serves pinned, exact-version local copies of those libraries
from doc_engine/vendor/assets/ instead, via Playwright request
interception, whenever the real network request would otherwise go to one
of those three CDN hosts. Anything not recognized still goes to the real
network - this only changes behavior for the specific libraries known to
sometimes fail.

Do not duplicate doc_engine/vendor/assets/ elsewhere - this module is the
single, shared way to reach it.
"""

import os

_VENDOR_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "doc_engine", "vendor", "assets"
)

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


def install_cdn_fallback(page) -> None:
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
