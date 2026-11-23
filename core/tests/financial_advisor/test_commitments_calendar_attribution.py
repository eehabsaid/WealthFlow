"""Commitments calendar: shared helper and rental/mortgage attribution, docs and AI-agent consistency."""
import json
import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from ai.services.app_knowledge.chunk_sources import page_chunks
from core.models import AssetInsurance, FixedAsset
from core.services.financial_advisor.commitments_calendar_service import CommitmentsCalendarService
from core.services.financial_advisor.commitments_calendar_service.event_shape import _shared_value

User = get_user_model()
ROOT = Path(settings.BASE_DIR)
TAB_ID = "commitments-calendar"


class AttributionTest(TestCase):
    def test_shared_value(self):
        self.assertEqual(_shared_value([1, 1, None]), 1)
        self.assertIsNone(_shared_value([1, 2]))
        self.assertIsNone(_shared_value([]))

    def test_highlights_keys_resolve_in_locales(self):
        user = User.objects.create_user(username="cc_hl", password="x12345678")
        asset = FixedAsset.objects.create(owner=user, name="A", asset_type="Other Assets", purchase_date=date(2025, 1, 1))
        AssetInsurance.objects.create(asset=asset, company="Co", expiry_date=date(2026, 12, 1), premium=100)
        payload = CommitmentsCalendarService(user, today=date(2026, 11, 22)).payload(date(2026, 11, 1), date(2026, 12, 31))
        en = json.loads((ROOT / "static" / "i18n" / "en.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["analysis"]["highlights"])
        for h in payload["analysis"]["highlights"]:
            self.assertIn(f"commitments_event_{h['event_type']}", en)
        for e in payload["events"]:
            self.assertIn(e["description_key"], en)


class DocsAndAgentTest(SimpleTestCase):
    def _json(self, *parts):
        return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))

    def test_inventory_registers_tab(self):
        route = next(r for r in self._json("ai", "doc_engine", "inventory.json") if r["route"] == "financial-advisor")
        self.assertIn(TAB_ID, [t["id"] for t in route["tabs"]])

    def test_guide_entry_describes_real_features(self):
        entry = self._json("ai", "doc_engine", "content", "page_descriptions.json")[f"financial-advisor::{TAB_ID}"]
        text = (entry["purpose"] + " ".join(entry["steps"])).lower()
        for word in ("month", "week", "agenda", "read-only", "bank"):
            self.assertIn(word, text)
        self.assertNotIn("goals", text)

    def test_ai_agent_knowledge_includes_tab(self):
        self.assertIn(f"page:financial-advisor::{TAB_ID}", {c["id"] for c in page_chunks()})

    def test_every_event_and_label_key_exists_in_all_locales(self):
        locales = {lang: self._json("static", "i18n", f"{lang}.json") for lang in ("en", "ar", "fr", "de")}
        keys = {k for k in locales["en"] if k.startswith("commitments_") or k.startswith("financial_advisor_tab_commitments")}
        for lang, data in locales.items():
            self.assertEqual(sorted(keys - set(data)), [], lang)
            self.assertFalse([k for k in keys if not str(data[k]).strip()], lang)
        js_dir = ROOT / "static" / "js" / "financial_advisor" / "commitments_calendar"
        used = set()
        for f in js_dir.glob("*.js"):
            used |= set(re.findall(r"""["'`](commitments_(?:view|category|kind|event|risk)_[a-z_]+)["'`]""", f.read_text(encoding="utf-8")))
        self.assertEqual(sorted(k for k in used if k not in locales["en"]), [])


class _Series:
    def __init__(self, events):
        self.events = events


class RentalMortgageAttributionTest(TestCase):
    def setUp(self):
        from core.models import Bank

        self.user = User.objects.create_user(username="cc_attr", password="x12345678")
        self.b1 = Bank.objects.create(owner=self.user, name="B1")
        self.b2 = Bank.objects.create(owner=self.user, name="B2")

    def _rental(self, name, bank):
        from core.models import AssetRental

        asset = FixedAsset.objects.create(owner=self.user, name=name, asset_type="Other Assets", purchase_date=date(2025, 1, 1))
        return AssetRental.objects.create(asset=asset, monthly_rent=100, bank=bank, contract_start=date(2026, 1, 1))

    def _events(self):
        from core.services.financial_advisor.commitments_calendar_service.events import CommitmentsEventsBuilder

        series = _Series([{"type": "rental_income", "date": date(2026, 11, 30), "amount": 200.0}])
        builder = CommitmentsEventsBuilder(self.user, date(2026, 11, 1), date(2026, 11, 30), series)
        return [e for e in builder.build() if e["event_type"] == "rental_income"]

    def test_single_rental_is_attributed(self):
        r = self._rental("R1", self.b1)
        (event,) = self._events()
        self.assertEqual((event["bank_id"], event["source_id"]), (self.b1.id, r.asset_id))

    def test_rentals_in_one_bank_keep_the_bank_but_not_one_asset(self):
        self._rental("R1", self.b1)
        self._rental("R2", self.b1)
        (event,) = self._events()
        self.assertEqual(event["bank_id"], self.b1.id)
        self.assertIsNone(event["source_id"])
        self.assertEqual(event["extra"]["count"], 2)

    def test_rentals_in_different_banks_are_not_pinned_to_the_first(self):
        self._rental("R1", self.b1)
        self._rental("R2", self.b2)
        (event,) = self._events()
        self.assertIsNone(event["bank_id"])
        self.assertIsNone(event["source_id"])
