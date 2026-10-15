"""Refusal detection (en/ar/fr/de) and tool-call extraction shapes."""

from __future__ import annotations

from django.test import SimpleTestCase

from core.services.ai.investigation.actions import extract_calls, strip_think, unavailable_tools
from core.services.ai.investigation.refusal import is_refusal

VALID = {"app_grep", "app_read_file", "app_data_query"}


class RefusalTest(SimpleTestCase):
    GIVE_UPS = (
        "I don't have access to your codebase, so I can't tell.", "I'm unable to view your data.", "I cannot read the file.",
        "As an AI, I cannot see your files.", "I do not have the tools for that.", "I don't have enough information to answer.",
        "لا أملك الوصول إلى بيانات التطبيق", "ليس لدي صلاحية للاطلاع على الملفات", "لا يمكنني الوصول إلى الكود",
        "Je n'ai pas accès aux fichiers du projet.", "Je ne peux pas accéder à vos données.", "Je ne dispose pas des outils nécessaires.",
        "Ich habe keinen Zugriff auf Ihre Daten.", "Ich kann nicht auf den Code zugreifen.", "Ich bin nicht in der Lage, das zu prüfen.",
        "", "   ",
    )
    REAL_ANSWERS = (
        "Your total is 5,000 EGP (Expense, September 2026).", "Expense has 0 rows for September 2026, so the total is 0.",
        "The function is defined at core/services/expenses/expense_service.py:12.", "إجمالي المصروفات 4,000 جنيه في سبتمبر",
        "Le total des dépenses est de 4 000 EGP.", "Die Ausgaben betragen 4.000 EGP.",
    )

    def test_capability_refusals_are_detected_in_four_languages(self):
        for text in self.GIVE_UPS:
            self.assertTrue(is_refusal(text, investigated=True), text)

    def test_real_answers_are_not_refusals(self):
        for text in self.REAL_ANSWERS:
            self.assertFalse(is_refusal(text, investigated=False), text)
            self.assertFalse(is_refusal(text, investigated=True), text)

    def test_not_found_counts_only_before_any_investigation(self):
        for text in ("I couldn't find that.", "لم أتمكن من العثور على ذلك", "Je n'ai pas trouvé.", "Ich konnte nichts finden."):
            self.assertTrue(is_refusal(text, investigated=False), text)
            self.assertFalse(is_refusal(text, investigated=True), text)

    def test_phrase_deep_inside_a_long_sourced_answer_is_prose(self):
        long_answer = ("Total: 4,000 EGP. " * 40) + " (I cannot access older years.)"
        self.assertFalse(is_refusal(long_answer, investigated=True))

    def test_extra_markers(self):
        self.assertTrue(is_refusal("Sorry, I could not produce an answer.", True, ("could not produce an answer",)))


class ActionsTest(SimpleTestCase):
    def test_native_calls_with_string_or_dict_arguments(self):
        res = {"tool_calls": [{"function": {"name": "app_grep", "arguments": '{"pattern": "x"}'}},
                              {"name": "app_read_file", "arguments": {"path": "manage.py"}}]}
        self.assertEqual(extract_calls(res, VALID), [("app_grep", {"pattern": "x"}), ("app_read_file", {"path": "manage.py"})])

    def test_text_json_shapes(self):
        shapes = ('<tool_call>{"name":"app_grep","arguments":{"pattern":"a{1}"}}</tool_call>',
                  '```json\n{"tool":"app_grep","args":{"pattern":"a{1}"}}\n```',
                  'I will search. {"function":"app_grep","parameters":{"pattern":"a{1}"}} done')
        for text in shapes:
            self.assertEqual(extract_calls({"content": text}, VALID), [("app_grep", {"pattern": "a{1}"})], text)

    def test_calling_syntax_copied_from_the_loop_history_is_a_tool_call(self):
        text = 'Calling app_grep({"pattern": "a{1}"}); app_read_file({"path": "manage.py"})'
        self.assertEqual(extract_calls({"content": text}, VALID),
                         [("app_grep", {"pattern": "a{1}"}), ("app_read_file", {"path": "manage.py"})])
        self.assertEqual(extract_calls({"content": "Calling not_offered({})"}, VALID), [])
        self.assertEqual(extract_calls({"content": "Calling app_grep({broken"}, VALID), [])

    def test_unoffered_tools_are_dropped_and_reported(self):
        res = {"tool_calls": [{"function": {"name": "create_scenario", "arguments": {}}}]}
        self.assertEqual(extract_calls(res, VALID), [])
        self.assertEqual(unavailable_tools(res, VALID), ["create_scenario"])
        self.assertEqual(extract_calls({"content": '{"name":"rm_rf","arguments":{}}'}, VALID), [])

    def test_at_most_three_calls_and_garbage_is_ignored(self):
        text = " ".join('{"name":"app_grep","arguments":{"pattern":"%d"}}' % i for i in range(6))
        self.assertEqual(len(extract_calls({"content": text}, VALID)), 3)
        self.assertEqual(extract_calls({"content": "{broken json {"}, VALID), [])
        self.assertEqual(extract_calls({"content": None}, VALID), [])

    def test_strip_think(self):
        self.assertEqual(strip_think("<think>plan</think>Answer"), "Answer")
        self.assertEqual(strip_think("<think>never closed"), "")
        self.assertEqual(strip_think(None), "")
