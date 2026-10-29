"""Judges, figure matching and the language signal: pure code, no model."""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase

from ai_training.services import judges
from ai_training.services.textutil import appears, figures, pool_of, script_of

Q = "How many expense records do I have?"
STEP = {"tool": "app_data_query", "arguments": {"model": "Expense", "aggregate": {"count": "*"}}, "result": '{"model":"Expense","total_matching":3,"result":{"count":3}}'}


class FiguresTest(SimpleTestCase):
    def test_readings_of_printed_figures(self):
        read = {p: v for p, v in figures("Total 13,229.56 and 1.234,50 and ١٢٣ and 12.500")}
        self.assertEqual(read["13,229.56"], {Decimal("13229.56")})
        self.assertEqual(read["1.234,50"], {Decimal("1234.50")})
        self.assertEqual(read["123"], {Decimal("123")})
        self.assertEqual(read["12.500"], {Decimal("12.500"), Decimal("12500")})   # ambiguous: both readings are kept

    def test_dates_and_list_numbers_are_not_figures(self):
        self.assertEqual([p for p, _ in figures("1. Rent on 2026-09-01 was 500.00\n2) Food 20.00")], ["500.00", "20.00"])

    def test_decimals_must_be_right_to_the_cent_whole_numbers_may_be_rounded(self):
        pool = pool_of('{"total":13229.5612}')
        self.assertTrue(appears("13,229.56", {Decimal("13229.56")}, pool))
        self.assertTrue(appears("13,230", {Decimal("13230")}, pool))
        self.assertFalse(appears("13,229.90", {Decimal("13229.90")}, pool))

    def test_script_is_the_only_language_signal(self):
        self.assertEqual(script_of("كم عدد المصروفات 3"), "ARABIC")
        self.assertEqual(script_of("How many 3"), "LATIN")
        self.assertEqual(script_of("12 34"), "")


class MethodChecksTest(SimpleTestCase):
    def check(self, answer="You have 3 expense records.", steps=None, reason="answered", question=Q):
        return judges.method_checks(question, answer, [STEP] if steps is None else steps, reason)

    def test_a_clean_run_passes(self):
        self.assertEqual(self.check(), [])

    def test_each_method_failure_has_its_own_reason(self):
        self.assertIn("did_not_look_at_data", self.check(steps=[]))
        self.assertIn("not_answered:budget", self.check(reason="budget"))
        self.assertIn("empty_answer", self.check(answer="  "))
        self.assertIn("leaked_tool_call_or_reasoning", self.check(answer="3 </think> records"))
        self.assertIn("leaked_tool_call_or_reasoning", self.check(answer='{"name": "app_data_query", "arguments": {"model": "Expense"}}'))
        self.assertIn("used_non_data_tool", self.check(steps=[STEP, {"tool": "app_read_file", "arguments": {}, "result": "{}"}]))
        self.assertIn("unscoped_model", self.check(steps=[{**STEP, "arguments": {"model": "AppSettings"}}]))
        self.assertIn("tool_error_in_run", self.check(steps=[STEP, {**STEP, "result": '{"error":"bad field"}'}]))
        self.assertIn("answer_in_other_language", self.check(answer="لديك 3 سجلات"))

    def test_a_figure_the_tools_never_returned_is_dropped(self):
        self.assertEqual([r for r in self.check(answer="You have 4 expense records.") if r.startswith("figure_not")], ["figure_not_in_tool_results:4"])

    def test_numbers_from_the_question_are_allowed(self):
        self.assertEqual(self.check(question="Show my last 3 expense records.", answer="Here are your last 3 records, 3 in total."), [])


class DataAndRepeatTest(SimpleTestCase):
    def test_expected_figures_must_all_be_in_the_answer(self):
        self.assertEqual(judges.data_check("Total 1,500.00 EGP", {"values": ["1500.00"]}), [])
        self.assertEqual(judges.data_check("Total 1,500.50 EGP", {"values": ["1500.00"]}), ["wrong_or_missing_figure:1500.00"])
        self.assertEqual(judges.data_check("anything", None), ["not_code_provable"])

    def test_repeat_needs_two_runs_with_the_same_figures(self):
        class T:
            def __init__(self, answer): self.answer = answer
        self.assertEqual(judges.repeat_check([T("3 records")]), ["not_repeated"])
        self.assertEqual(judges.repeat_check([T("You have 3 records."), T("3 records in total")]), [])
        self.assertEqual(judges.repeat_check([T("You have 3 records."), T("You have 4 records.")]), ["not_repeatable"])
        self.assertEqual(judges.repeat_check([T("3 records, 50.00"), T("3 records")]), ["not_repeatable"])
        exp = {"values": ["500.00"]}
        self.assertEqual(judges.repeat_check([T("500.00 at 49.995"), T("500.00 at 49.9950, month 8")], exp), [])
        self.assertEqual(judges.repeat_check([T("500.00"), T("510.00")], exp), ["not_repeatable"])
