"""Documentation capture, generated documents and the Settings buttons all use ONE folder: <project>/docs (never ai/docs)."""

import os

from django.conf import settings
from django.test import SimpleTestCase

from ai.doc_engine import config
from core.views.settings.documentation import documentation_constants as constants


class DocsFolderTest(SimpleTestCase):
    def test_the_engine_writes_under_the_project_docs_folder(self):
        docs = os.path.join(str(settings.BASE_DIR), "docs")
        self.assertEqual(config.DOCS_DIR, docs)
        self.assertEqual(config.SCREENSHOTS_DIR, os.path.join(docs, "screenshots"))
        self.assertEqual(config.LATEST_SCREENSHOTS_DIR, os.path.join(docs, "screenshots", "latest"))
        self.assertEqual(config.GENERATED_DIR, os.path.join(docs, "generated"))

    def test_the_settings_buttons_open_the_folder_the_engine_writes(self):
        for name in ("DOCS_DIR", "SCREENSHOTS_DIR", "GENERATED_DIR", "RUNTIME_DIR", "STATUS_FILE", "CANCEL_FILE"):
            self.assertEqual(getattr(constants, name), getattr(config, name), name)

    def test_nothing_points_into_the_ai_package(self):
        ai_dir = os.path.join(str(settings.BASE_DIR), "ai") + os.sep
        for name in ("DOCS_DIR", "SCREENSHOTS_DIR", "GENERATED_DIR", "RUNTIME_DIR"):
            self.assertFalse(getattr(config, name).startswith(ai_dir), name)
