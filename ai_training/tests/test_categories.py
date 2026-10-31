"""The 16-category generator, the language check, the clarify judge and the model names of the second training."""

from __future__ import annotations

import datetime
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from ai_training.services import eval_report, generator, judges, langcheck, ollama_stage, phrasing, taxonomy
from ai_training.services.case import make, norm_text
from ai_training.services.config import load
from ai_training.tests.eval_support import add_expenses
from core.models import Budget, Expense, ExpenseCategory, ExpenseSubcategory, Goal
from core.tests.ai.investigation.support import make_user, seed_tenant


class SeededData(TestCase):
    def setUp(self):
        self.user = make_user("cat_user")
        seed_tenant(self.user, "Q", expenses=3, amount="50.00")
        add_expenses(self.user, ["10.00", "20.00"])
        other = make_user("cat_other")
        seed_tenant(other, "Z", expenses=7, amount="99.00")
        self.cases = {c.key: c for c in generator.generate(self.user)}

    def test_cases_carry_category_language_and_level_and_no_other_users_figures(self):
        self.assertTrue(all({"category", "lang", "level", "judge"} <= set(c.meta) for c in self.cases.values()))
        self.assertTrue({"en", "ar", "fr", "de"} <= {c.meta["lang"] for c in self.cases.values()})
        self.assertFalse(any("99.00" in str(c.expected["values"]) for c in self.cases.values()))
        self.assertEqual(self.cases["Expense:count"].meta["category"], "expenses")

    def test_no_duplicate_wording_and_no_test_kind_in_training(self):
        texts = [norm_text(c.question) for c in self.cases.values()]
        self.assertEqual(len(texts), len(set(texts)))
        self.assertFalse(any(k.startswith("eval:") for k in self.cases))

    def test_translated_wording_uses_the_apps_own_labels(self):
        ar = next(c for k, c in self.cases.items() if k.startswith("Expense:count|ar"))
        self.assertIn("المصاريف", ar.question)
        self.assertIsNone(phrasing.say("count", "fr", 0, label=None))

    def test_category_questions_are_proven_from_real_rows(self):
        cat = ExpenseCategory.objects.filter(owner=self.user).first()
        sub = ExpenseSubcategory.objects.create(category=cat, name="Sub A")
        Expense.objects.filter(owner=self.user, amount="10.00").update(subcategory=sub)
        Budget.objects.create(owner=self.user, name="Food limit", amount=Decimal("200"), amount_base=Decimal("200"))
        Goal.objects.create(owner=self.user, name="Car", target_amount=Decimal("1000"), current_saved_amount=Decimal("250"), target_date=datetime.date(2030, 1, 1))
        found = {c.key: c for c in generator.generate(self.user)}
        left = next(c for k, c in found.items() if k.startswith("goal_left"))
        self.assertEqual(left.expected["values"], ["750.00"])
        what_if = next(c for k, c in found.items() if k.startswith("whatif_cut_month"))
        self.assertEqual(what_if.meta["category"], "what_if")
        self.assertIn("q_nosub", found)
        self.assertEqual(found["q_nosub"].expected["values"], [4])

    def test_ambiguous_questions_exist_only_when_the_data_is_really_ambiguous(self):
        self.assertNotIn("amb_spend", self.cases)            # one month of expenses only: "how much did I spend?" has one answer


class LanguageAndJudgeTest(SimpleTestCase):
    def test_arabic_by_script_and_latin_languages_by_the_apps_own_words(self):
        self.assertEqual(langcheck.detect("لديك 6 أهداف"), "ar")
        self.assertEqual(langcheck.detect("Vous avez 6 objectifs et le montant total est de 1 200,00 dans vos dépenses."), "fr")
        self.assertEqual(langcheck.detect("Sie haben 6 Ziele und der Gesamtbetrag beträgt 1.200,00 für Ihre Ausgaben."), "de")
        self.assertEqual(langcheck.detect("Total: 1200.00"), "")

    def test_french_must_be_confirmed_and_an_english_answer_to_a_french_question_fails(self):
        fr_q = "Combien d'enregistrements « Dépenses » ai-je ?"
        self.assertEqual(judges.language_reasons(fr_q, "You have 6 expense records in your data.", "fr"), ["answer_in_other_language"])
        self.assertEqual(judges.language_reasons(fr_q, "6", "fr"), ["language_not_confirmed"])
        self.assertEqual(judges.language_reasons(fr_q, "Vous avez 6 dépenses enregistrées dans vos données.", "fr"), [])
        self.assertEqual(judges.language_reasons("How many?", "6", "en"), [])

    def clarify(self, answer, steps=(), question="How much did I spend?"):
        trace = SimpleNamespace(question=question, answer=answer, steps=list(steps), reason="answered",
                                expected=make("amb", question, [], category="ambiguous", judge="clarify").expected)
        return judges.judge_attempt(trace)

    def test_clarify_judge_accepts_a_question_back_and_rejects_a_guess(self):
        self.assertEqual(self.clarify("Which month do you mean?"), [])
        self.assertIn("guessed_instead_of_asking", self.clarify("You spent 12,345.00 in total. Which month do you mean?"))
        self.assertIn("no_clarifying_question", self.clarify("You spent a lot."))

    def test_repeat_check_needs_no_equal_wording_for_clarify_cases(self):
        both = [SimpleNamespace(answer="Which month?"), SimpleNamespace(answer="Which period do you mean?")]
        self.assertEqual(judges.repeat_check(both, make("a", "q", [], category="ambiguous", judge="clarify").expected), [])


class NamesAndReportTest(SimpleTestCase):
    def test_second_model_gets_a_distinct_name_beside_the_first(self):
        cfg = load(original_model="", best_model="", new_model="")
        self.assertEqual((cfg.model_suffix, cfg.previous_suffixes), ("-agent2", ("-agent",)))
        for current in ("m:27b", "m:27b-agent", "m:27b-agent2"):
            self.assertEqual(ollama_stage.base_name(current, cfg), "m:27b")
        self.assertEqual(ollama_stage.new_name("m:27b", cfg.model_suffix), "m:27b-agent2")

    def row(self, key, ok, reasons=(), cat="expenses"):
        return {"key": key, "passed": ok, "reasons": list(reasons), "seconds": 1.0, "category": cat, "lang": "en"}

    def test_report_numbers_regressions_tool_use_hallucination_and_language(self):
        best = [self.row("a", True), self.row("b", True), self.row("c", False)]
        new = [self.row("a", True), self.row("b", False, ["figure_not_in_tool_results:5"]), self.row("c", False, ["did_not_look_at_data", "answer_in_other_language"])]
        self.assertEqual(eval_report.regressions(best, new), ["b"])
        s = eval_report.stats(new)
        self.assertEqual((s["hallucinated"], s["tool_correct"], s["language_ok"]), (1, 66.7, 66.7))
        self.assertEqual(s["by_category"]["expenses"]["passed"], 1)
        self.assertIn("expenses", taxonomy.TABLE_CATEGORY.values())

    def test_explicit_model_names_from_config_win(self):
        cfg = load(original_model="m:150k", best_model="m:agent", new_model="m:agent2")
        self.assertEqual(ollama_stage.base_name("m:agent", cfg), "m:150k")
        from ai_training.services import evaluate
        self.assertEqual(evaluate.names("m:agent", cfg), ("m:150k", "m:agent", "m:agent2"))
