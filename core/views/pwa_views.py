"""PWA endpoints: web app manifest, service worker and offline fallback page.

The service worker is rendered from a template and served from the site root
(not /static/) so its scope covers the whole app. All three routes are public
(see core/middleware/login_required.py) because the browser fetches them
before/without a session.
"""

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_GET

PWA_CACHE_VERSION = "v4"
PWA_THEME_COLOR = "#0a0f1e"
OFFLINE_URL = "/offline/"

# Same-origin static files pre-cached at install so the shell opens offline.
PWA_PRECACHE_STATIC = (
    "images/pwa/icon-192.png",
    "images/pwa/icon-512.png",
    "images/favicon.ico",
    "js/pwa/offline.js",
    "i18n/en.json",
)


@require_GET
def manifest_view(request):
    icons = [
        {"src": static("images/pwa/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": static("images/pwa/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": static("images/pwa/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ]
    data = {
        "name": "WealthFlow",
        "short_name": "WealthFlow",
        "id": "/",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": PWA_THEME_COLOR,
        "theme_color": PWA_THEME_COLOR,
        "categories": ["finance", "productivity"],
        "icons": icons,
    }
    response = JsonResponse(data, content_type="application/manifest+json")
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
def service_worker_view(request):
    context = {
        "cache_version": PWA_CACHE_VERSION,
        "precache_json": json.dumps([static(p) for p in PWA_PRECACHE_STATIC] + [OFFLINE_URL]),
        "offline_url": OFFLINE_URL,
    }
    response = render(request, "pwa/service-worker.js", context, content_type="application/javascript")
    response["Cache-Control"] = "no-cache"
    response["Service-Worker-Allowed"] = "/"
    return response


@require_GET
def offline_view(request):
    return render(request, "pwa/offline.html", {"theme_color": PWA_THEME_COLOR})
