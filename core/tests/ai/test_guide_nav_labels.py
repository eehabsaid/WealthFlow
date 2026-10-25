"""The guide's "Navigate to A -> B" steps start from a real sidebar label (nav_* keys in the English i18n file), never a paraphrase;
B may be a tab, so only A is checked."""

import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

ROOT = Path(settings.BASE_DIR)


class GuideNavLabelsTest(SimpleTestCase):
    def test_navigate_steps_start_from_a_real_sidebar_label(self):
        labels = {v for k, v in json.loads((ROOT / "static/i18n/en.json").read_text("utf8")).items() if k.startswith("nav_") and isinstance(v, str)}
        text = (ROOT / "doc_engine/content/page_descriptions.json").read_text("utf8")
        bad = []
        for first, _second in re.findall(r"Navigate to ([^\">]+?) -> ([^\">]+?)\.\"", text):
            if first not in labels:
                bad.append(first)
        self.assertEqual(bad, [])
