"""The default Privacy/Terms text carries clearly marked operator fields (name, contact,
retention period, governing law) in every language, so the owner can fill them in the
Settings > Legal Text editor, and the 'legal review needed' notice stays in place."""
import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

LANGS = ("en", "ar", "fr", "de")
FIELDS = {
    "privacy_s1_body": ["[[OPERATOR_NAME]]"],
    "privacy_s7_body": ["[[RETENTION_PERIOD]]"],
    "privacy_s8_body": ["[[CONTACT_EMAIL]]"],
    "terms_s9_body": ["[[CONTACT_EMAIL]]", "[[GOVERNING_LAW]]"],
}


def _load(lang):
    return json.loads((Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


class LegalOperatorPlaceholderTests(SimpleTestCase):
    def test_every_language_has_every_marked_field(self):
        for lang in LANGS:
            data = _load(lang)
            for key, tokens in FIELDS.items():
                for token in tokens:
                    self.assertIn(token, data[key], f"{lang}.json {key} is missing {token}")

    def test_legal_review_notice_is_kept(self):
        for lang in LANGS:
            self.assertTrue(_load(lang).get("legal_draft_notice", "").strip(), lang)
