"""The Documentation Generator reads the app's real locale files, and the fixed words of a guide come from them."""

import json
import os

from django.test import SimpleTestCase

from doc_engine.document_generator.labels import FIXED, GUIDE_TYPES, fixed_labels, guide_type_label
from doc_engine.document_generator.validation import I18N_DIR

KEYS = [key for key, _ in FIXED.values()] + [key for key, _ in GUIDE_TYPES.values()]


def locale(lang):
    with open(os.path.join(I18N_DIR, f"{lang}.json"), encoding="utf-8") as handle:
        return json.load(handle)


class DocumentationLabelsTest(SimpleTestCase):
    def test_the_generator_looks_in_the_folder_that_exists(self):
        for lang in ("en", "ar", "fr", "de"):
            self.assertTrue(os.path.isfile(os.path.join(I18N_DIR, f"{lang}.json")), lang)

    def test_every_fixed_label_exists_in_all_four_locales(self):
        for lang in ("en", "ar", "fr", "de"):
            data = locale(lang)
            self.assertEqual([k for k in KEYS if not data.get(k)], [], lang)

    def test_labels_follow_the_language_and_english_never_shows_arabic(self):
        self.assertEqual(fixed_labels(locale("en"))["lbl_generated"], "Generated")
        self.assertEqual(fixed_labels(locale("fr"))["toc_title"], "Table des matières")
        self.assertEqual(fixed_labels(locale("de"))["steps_title"], "Schritte")
        self.assertEqual(fixed_labels(locale("ar"))["purpose_title"], "الغرض")
        self.assertEqual(guide_type_label(locale("ar"), "user"), "دليل المستخدم")
        for text in list(fixed_labels({}).values()) + [guide_type_label({}, "admin")]:
            self.assertTrue(text.isascii(), text)                        # a locale without the key falls back to English
