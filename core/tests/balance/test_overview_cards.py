"""Balance > Overview: only currencies with a positive amount get a card, and an
all-zero balance shows a friendly empty state (frontend rule; no backend change).

The render code is plain browser JS, so these tests guard the source contract
and the four-language strings; the behaviour itself is exercised in a real
browser by tests/modules/balance/overview.py.
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

LANGS = ("en", "ar", "fr", "de")
KEYS = ("balance_overview_empty_title", "balance_overview_empty_desc")
_PLACEHOLDER = re.compile(r"\{[a-zA-Z0-9_]+\}")


def _overview_js():
    return (Path(settings.BASE_DIR) / "static" / "js" / "balance" / "overview.js").read_text(encoding="utf-8")


class BalanceOverviewCardsTests(SimpleTestCase):
    def test_cards_are_filtered_on_the_numeric_amount(self):
        src = _overview_js()
        self.assertIn("Number(totals[lookupKey])", src)
        self.assertIn(".filter((item) => item.cardValue > 0)", src)

    def test_empty_state_replaces_cards_when_none_remain(self):
        src = _overview_js()
        self.assertIn('id="balOverviewEmpty"', src)
        self.assertIn('data-i18n="balance_overview_empty_title"', src)
        self.assertIn('data-i18n="balance_overview_empty_desc"', src)

    def test_empty_state_strings_exist_in_every_language(self):
        for lang in LANGS:
            path = Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in KEYS:
                self.assertTrue(data.get(key, "").strip(), f"{lang}.json is missing {key}")

    def test_empty_state_placeholders_match_across_languages(self):
        base = {}
        for lang in LANGS:
            path = Path(settings.BASE_DIR) / "static" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in KEYS:
                found = sorted(_PLACEHOLDER.findall(data[key]))
                base.setdefault(key, found)
                self.assertEqual(found, base[key], f"{lang}.json {key} placeholders differ")
