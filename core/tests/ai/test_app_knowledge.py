"""Zip 2 A/B: workflow knowledge retrieval, the code-derived data-flows file, and the question classifier."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase

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


class RetrievalTests(TestCase):   # reads AppSettings (semantic switch)
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

    def test_arabic_questions_reach_the_english_knowledge(self):
        ids = self.ids("أين أسجل شراء لابتوب؟ في الأصول أم المصروفات؟")
        self.assertTrue(any(i.startswith("flow:Fixed assets") for i in ids), ids)
        self.assertTrue(any(i.startswith("flow:Expenses") or i.startswith("flow:Double") for i in ids), ids)

    def test_french_questions_reach_the_english_knowledge(self):
        for q in ("Où dois-je enregistrer le prix d'un ordinateur acheté ? Dans les actifs ou les dépenses ?",
                  "Si j'ai acheté un téléphone, où saisir le prix : actifs immobilisés ou dépenses ?"):
            ids = self.ids(q)
            self.assertTrue(any(i.startswith("flow:Fixed assets") for i in ids), (q, ids))
            self.assertTrue(any(i.startswith(("flow:Expenses", "flow:Double", "flow:Mirroring")) for i in ids), (q, ids))
        self.assertTrue(any("credit_card_payment" in i for i in self.ids("Où enregistrer le paiement de ma carte de crédit ?")))
        self.assertTrue(any("renovations" in i or i.startswith("flow:Fixed assets") for i in self.ids("Comment saisir les frais de rénovation de mon appartement ?")))

    def test_german_questions_reach_the_english_knowledge(self):
        for q in ("Wo soll ich den Kaufpreis eines Computers erfassen: Vermögenswerte oder Ausgaben?",
                  "Wenn ich ein Handy gekauft habe, wo buche ich den Preis, bei den Anlagegütern oder den Ausgaben?"):
            ids = self.ids(q)
            self.assertTrue(any(i.startswith("flow:Fixed assets") for i in ids), (q, ids))
            self.assertTrue(any(i.startswith(("flow:Expenses", "flow:Double", "flow:Mirroring")) for i in ids), (q, ids))
        self.assertTrue(any("credit_card_payment" in i for i in self.ids("Wo erfasse ich die Zahlung meiner Kreditkarte?")))
        self.assertTrue(any("renovations" in i or i.startswith("flow:Fixed assets") for i in self.ids("Wie erfasse ich die Renovierungskosten meiner Wohnung?")))

    def test_accents_and_umlauts_fold_instead_of_splitting_words(self):
        from core.services.ai.app_knowledge.query_terms_fr_de import fold, foreign_terms

        self.assertEqual(fold("Dépenses Vermögenswerte Straße"), "depenses vermogenswerte strasse")
        self.assertIn("expense", foreign_terms("mes dépenses"))
        self.assertIn("expense", foreign_terms("meine Ausgaben"))
        self.assertIn("price", foreign_terms("der Kaufpreis"))
        self.assertEqual(foreign_terms("how much did I spend"), set())
        self.assertEqual(foreign_terms(LAPTOP), set())   # English "or"/"in"/"its" must never map to French/German words
        from core.services.ai.app_knowledge.scoring import expand_query
        self.assertNotIn("gold", expand_query(LAPTOP))
        self.assertEqual(fold("مصروفات ٢"), "مصروفات ٢")  # Arabic untouched

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
                  "أين أسجل شراء لابتوب؟",
                  "Où dois-je enregistrer mon achat d'ordinateur ?", "Comment saisir une dépense de carte ?",
                  "Si j'ai acheté un portable, où le noter ?", "Est-ce mieux de le mettre en dépense ?",
                  "Wo erfasse ich einen Computer-Kauf?", "Soll ich das als Ausgabe oder Vermögenswert buchen?",
                  "Wenn ich ein Auto verkauft habe, wo trage ich das Geld ein?"):
            self.assertTrue(ak.is_workflow_question(q), q)

    def test_lookups_and_actions_are_not(self):
        for q in ("how much did I spend in June 2026?", "what is my balance", "show salary for March",
                  "add an expense of 50 for lunch", "hello", "", "x" * 600,
                  "Quel est mon solde ?", "Combien ai-je dépensé en juin ?", "Ajoute une dépense de 50",
                  "Wie hoch sind meine Ausgaben im März?", "Füge eine Ausgabe von 50 hinzu", "Zeige mein Gehalt"):
            self.assertFalse(ak.is_workflow_question(q), q)
