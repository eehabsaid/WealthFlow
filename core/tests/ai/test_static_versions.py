"""Changed static assets must get a new URL version, otherwise the service worker (stale-while-revalidate on
/static/) and the browser keep serving the old file for a visit or two."""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from core.views import pwa_views


class StaticVersionTests(SimpleTestCase):
    def read(self, rel):
        return (Path(settings.BASE_DIR) / rel).read_text(encoding="utf-8")

    def test_ai_scripts_share_the_ai_css_version(self):
        scripts = set(re.findall(r"js/ai/(?:ai_feedback|ai_messages|ai_shell|learned_answers/la_modal)\.js' %\}\?v=(\d+)",
                                 self.read("templates/partials/scripts/04_ai.html")))
        css = set(re.findall(r"css/ai/index\.css' %\}\?v=(\d+)", self.read("templates/index.html")))
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts, css)
        self.assertNotEqual(next(iter(scripts)), "1784452207")   # the version the stale copies were cached under

    def test_service_worker_cache_was_bumped(self):
        self.assertNotEqual(pwa_views.PWA_CACHE_VERSION, "v1")
