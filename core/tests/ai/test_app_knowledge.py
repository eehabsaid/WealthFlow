"""Zip 2 A/B: workflow knowledge retrieval, the code-derived data-flows file, and the question classifier."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from core.services.ai import app_knowledge as ak
from core.services.ai.app_knowledge.chunks import get_chunks
from core.services.ai.app_knowledge.data_flows import build_data_flows_markdown, data_flows_path

LAPTOP = "if i bought a laptop where should i record its price? in assets, or in expenses?"


class DataFlowsFileTests(SimpleTestCase):
    def test_committed_file_matches_code(self):
        self.assertEqual(
            data_flows_path().read_text(encoding="utf-8").replace("\r\n", "\n"), build_data_flows_markdown(),
            "ai_knowledge/10_data_flows.md is stale: run python manage.py generate_ai_knowledge")

    def test_facts_come_from_code(self):
        from core.constants import ASSET_TYPES

        text = build_data_flows_markdown()
        for value, _ in ASSET_TYPES:
            self.assertIn(value, text)
        self.assertIn("NOT written as an Expense row", text)
        self.assertIn("Expense payment method 'Other': deducts a balance entry: no", text)
        self.assertIn("Cash': needs a bank account: no", text)
        self.assertIn("asset_acquisition_cost", text)


class ChunkTests(SimpleTestCase):
    def test_all_three_sources_present_and_small(self):
        chunks = get_chunks(force=True)
        kinds = {c["source"] for c in chunks}
        self.assertEqual(kinds, {"flow", "page", "code"})
        self.assertGreaterEqual(sum(1 for c in chunks if c["source"] == "page"), 100)  # page_descriptions.json is read
        self.assertTrue(all(len(c["text"]) <= 760 for c in chunks))

    def test_assistant_plumbing_is_not_knowledge(self):
        locations = {c["location"] for c in get_chunks()}
        self.assertFalse([p for p in locations if "/services/ai/" in p or "/views/ai_chat/" in p])
        self.assertIn("core/services/shared/expense_mirror_engine.py", locations)


class RetrievalTests(SimpleTestCase):
    def ids(self, q):
        return [c["id"] for _, c in ak.retrieve_knowledge(q)]

    def test_laptop_question_gets_asset_and_expense_flow_chunks(self):
        ids = self.ids(LAPTOP)
        self.assertTrue(any(i.startswith("flow:Fixed assets") for i in ids), ids)
        self.assertTrue(any(i.startswith("flow:Expenses") or i.startswith("flow:Mirroring") or i.startswith("flow:Double") for i in ids), ids)
        self.assertLessEqual(sum(len(c["text"]) for _, c in ak.retrieve_knowledge(LAPTOP)), 2400)

    def test_other_workflow_questions_find_their_own_sources(self):
        self.assertTrue(any("credit_card_payment" in i for i in self.ids("where do I record my credit card payment?")))
        self.assertTrue(any("renovations" in i or i.startswith("flow:Fixed assets") for i in self.ids("how should I enter renovation costs of my apartment?")))

    def test_nothing_is_hard_coded_for_the_trigger_question(self):
        root = Path(settings.BASE_DIR)
        scanned = list((root / "core/services/ai/app_knowledge").glob("*.py")) + list((root / "core/views/ai_chat/chat_pipeline").glob("*.py"))
        scanned.append(root / "ai_knowledge" / "10_data_flows.md")
        offenders = [str(p) for p in scanned if "laptop" in p.read_text(encoding="utf-8").lower()]
        self.assertEqual(offenders, [])


class QuestionKindTests(SimpleTestCase):
    def test_workflow_questions(self):
        for q in (LAPTOP, "where do I record my credit card payment?", "how should I enter renovation costs?",
                  "should I add my car insurance as an expense?", "If I sold my car, where do I put the money?",
                  "أين أسجل شراء لابتوب؟"):
            self.assertTrue(ak.is_workflow_question(q), q)

    def test_lookups_and_actions_are_not(self):
        for q in ("how much did I spend in June 2026?", "what is my balance", "show salary for March",
                  "add an expense of 50 for lunch", "hello", "", "x" * 600):
            self.assertFalse(ak.is_workflow_question(q), q)
