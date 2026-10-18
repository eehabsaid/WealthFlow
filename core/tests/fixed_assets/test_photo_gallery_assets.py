"""Asset Details photo gallery: static wiring, locale keys and the 200-line rule."""

import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

GALLERY_JS = "static/js/fixed_assets/asset_detail_view/photo_gallery.js"
KEYS = ("previous_photo", "next_photo")


class PhotoGalleryAssetTests(SimpleTestCase):
    def read(self, rel):
        return (Path(settings.BASE_DIR) / rel).read_text(encoding="utf-8")

    def test_locales_have_arrow_labels(self):
        for lang in ("en", "ar", "fr", "de"):
            data = json.loads(self.read(f"static/i18n/{lang}.json"))
            for key in KEYS:
                self.assertTrue(data.get(key), f"{lang}.json missing {key}")

    def test_gallery_script_loads_before_its_callers(self):
        html = self.read("templates/partials/scripts/07_fixed_assets.html")
        order = re.findall(r"asset_detail_view/(photo_gallery|non_real_estate_modal|entry)\.js", html)
        self.assertEqual(order[0], "photo_gallery")
        self.assertEqual(set(order), {"photo_gallery", "non_real_estate_modal", "entry"})

    def test_gallery_css_is_imported(self):
        self.assertIn("photo_gallery.css", self.read("static/css/fixed_assets/index.css"))

    def test_files_stay_under_200_lines(self):
        for rel in (GALLERY_JS, "static/css/fixed_assets/photo_gallery.css", "static/css/fixed_assets/base_layout.css"):
            self.assertLessEqual(len(self.read(rel).splitlines()), 200, rel)
