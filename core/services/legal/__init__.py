"""Legal text service package.

content.py  - defaults from the i18n files, DB overrides, current version, cache.
publish.py  - validation and publishing of a new version.
consent.py  - who must (re)accept the current version, and recording acceptance.
"""

from core.services.legal.consent import accept_current, needs_reconsent
from core.services.legal.content import (
    DOCS,
    LANGS,
    clear_cache,
    current_label,
    get_document,
    get_editor_payload,
)
from core.services.legal.publish import LegalPublishError, publish_version

__all__ = [
    "DOCS",
    "LANGS",
    "LegalPublishError",
    "accept_current",
    "clear_cache",
    "current_label",
    "get_document",
    "get_editor_payload",
    "needs_reconsent",
    "publish_version",
]
