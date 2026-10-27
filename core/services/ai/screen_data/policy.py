"""What the live-screen-data tool may call. The tool reads the same GET endpoints the app's own screens fetch, so the rule is
structural: only /api/ views that answer GET, nothing that manages users, secrets, settings, billing, backups, files or the AI
itself, and nothing whose path says it does something (refresh, create, restore ...). Every denied family is listed here once."""

from __future__ import annotations

import re

API_ROOT = "/api/"
DENIED_PREFIXES = (
    "/api/auth/", "/api/users", "/api/roles", "/api/settings/", "/api/billing/", "/api/account/", "/api/legal/",
    "/api/onboarding/", "/api/financial-advisor/ai/", "/api/ai-platform/", "/api/export/", "/api/import/",
    "/api/translations", "/api/scan-translations", "/api/reports/", "/api/documents/", "/api/fixed-assets/photo/",
    "/api/fixed-assets/reports/",
)
DENIED_SEGMENTS = frozenset({
    "refresh", "create", "delete", "restore", "process-due", "generate-current", "mark-paid", "fake-complete", "webhook",
    "export", "download", "upload", "capture", "scrape", "calculate", "duplicate", "favorite", "use",
})
_SEGMENT = re.compile(r"[^/]+")


def allowed(path: str) -> bool:
    """True when a GET on this path (a route pattern or a real URL) may be offered and executed."""
    if not str(path).startswith(API_ROOT) or str(path).startswith(DENIED_PREFIXES):
        return False
    return not DENIED_SEGMENTS.intersection(s.lower() for s in _SEGMENT.findall(str(path)))
