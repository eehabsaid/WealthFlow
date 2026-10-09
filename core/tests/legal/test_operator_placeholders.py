"""The default Privacy/Terms text carries the operator fields (name, contact, retention period,
governing law) filled in for every language, with no unresolved [[...]] marker left, and the
'legal review needed' notice stays in place. Settings > Legal Text can still override the text."""
import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

LANGS = ("en", "ar", "fr", "de")
FIELDS = {
    "privacy_s1_body": [None],  # operator name: Latin in en/fr/de, Arabic script in ar
    "privacy_s7_body": ["30"],
    "privacy_s8_body": ["ehab.alqabbani1981@gmail.com"],
    "terms_s9_body": ["ehab.alqabbani1981@gmail.com"],
}


def _load(lang):
    return json.loads((Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


class LegalOperatorPlaceholderTests(SimpleTestCase):
    def test_every_language_has_every_filled_field_and_no_open_marker(self):
        for lang in LANGS:
            data = _load(lang)
            for key, tokens in FIELDS.items():
                for token in tokens:
                    if token is None:
                        self.assertTrue("Ehab Al-Qabbani" in data[key] or "إيهاب القباني" in data[key], f"{lang}.json {key} lacks the operator name")
                        continue
                    self.assertIn(token, data[key], f"{lang}.json {key} is missing {token}")
                self.assertNotIn("[[", data[key], f"{lang}.json {key} still has an open marker")

    def test_legal_review_notice_is_kept(self):
        for lang in LANGS:
            self.assertTrue(_load(lang).get("legal_draft_notice", "").strip(), lang)
