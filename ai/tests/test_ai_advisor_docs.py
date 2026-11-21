"""Settings > AI Advisor is a tab bar of sections (one visible at a time): every section is documented under its own key, the guide
the AI writes lists them all, and the capture engine photographs them one by one instead of stacking them."""

import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from ai.doc_engine.config import CONTENT_FILE
from ai.doc_engine.models import DocumentationModel
from ai.doc_engine.playwright_engine.capture_runner.capture import CaptureMixin
from ai.services.investigation.compose_descriptions import page_evidence

KEY = "settings::settings-aiadvisor"


def section_keys() -> list[str]:
    """The i18n keys of the sections the page offers, read from the page's own list (layout_helpers.js + nav.js)."""
    root = Path(settings.BASE_DIR) / "static" / "js" / "settings" / "ai_advisor"
    groups = re.findall(r'"(ai_grp_\w+)",\s*"[^"]+",', (root / "layout_helpers.js").read_text(encoding="utf-8"))
    return groups + ["ai_grp_limits"]


class AIAdvisorDocsTests(SimpleTestCase):
    def test_every_section_has_its_own_documented_entry(self):
        with open(CONTENT_FILE, encoding="utf-8") as handle:
            content = json.load(handle)
        keys = section_keys()
        self.assertEqual(len(keys), 11)
        for key in keys:
            entry = content.get(f"{KEY}::{key}")
            self.assertTrue(entry and entry["purpose"] and entry["steps"], f"{key} is not documented")

    def test_the_guide_lists_every_section_under_the_tab(self):
        tab = page_evidence("settings", ["settings-aiadvisor"])["tabs"]["settings-aiadvisor"]
        self.assertEqual(len(tab["items"]), 11)
        self.assertIn("Agent limits", [i["name"] for i in tab["items"]])

    def test_a_captured_section_is_a_documented_child_of_the_tab(self):
        with open(CONTENT_FILE, encoding="utf-8") as handle:
            content = json.load(handle)
        page = {"route": "settings", "tab_id": "settings-aiadvisor", "is_admin": True}
        pages = [{**page, "page_title": "AI Advisor", "filename": "a.png", "screenshot_path": "screenshots/a.png", "capture_timestamp": "1"},
                 {**page, "nested_tab_id": "ai_grp_agent", "page_title": "Agent limits", "filename": "b.png",
                  "screenshot_path": "screenshots/b.png", "capture_timestamp": "2"}]
        model = DocumentationModel({"pages": pages}, content)
        self.assertEqual(model.validation_warnings, [])
        tab = model.nodes[0].children[0]
        self.assertEqual([c.title for c in tab.children], ["Agent Limits"])

    def test_the_capture_no_longer_forces_every_section_visible(self):
        import inspect
        source = inspect.getsource(CaptureMixin.capture_screenshot)
        self.assertNotIn(".aia-card[hidden]", source)
        self.assertNotIn(".aia-chips { display: none", source)
