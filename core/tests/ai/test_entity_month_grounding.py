"""Validator root cause of "couldn't match month 2026-08": a correct month was flagged because the evidence stores months as
names ("month":"August","year":2026) in either key order and the question asked for a whole year."""

from django.test import SimpleTestCase

from core.views.ai_chat.chat_pipeline.coverage import period_in_context
from core.views.ai_chat.chat_pipeline.entity_check import check_entities

EVIDENCE = '{"salary":{"entries":[{"company":"Acme","month":"August","year":2026,"paid":"1"},{"year": 2026, "month": 7, "paid": 2},{"month":"Jun","note":"x","year":2026}]}}'


class MonthGroundingTests(SimpleTestCase):
    def test_named_numeric_abbreviated_and_iso_months_are_found(self):
        self.assertTrue(all(period_in_context(EVIDENCE, p) for p in ("2026-08", "2026-07", "2026-06")))
        self.assertTrue(period_in_context("paid on 2026-09-14", "2026-09"))
        self.assertFalse(period_in_context(EVIDENCE, "2026-05"))
        self.assertFalse(period_in_context(EVIDENCE, "2025-08"))

    def test_correct_month_is_not_flagged(self):
        self.assertEqual(check_entities("In August 2026 you were paid 1.", "list salaries", EVIDENCE), (1, []))

    def test_whole_year_question_covers_its_months(self):
        self.assertEqual(check_entities("In August 2026 you were paid 1.", "list paid salaries for year 2026", "no rows"), (0, []))

    def test_invented_month_is_still_flagged(self):
        self.assertEqual(check_entities("In May 2026 you were paid 9.", "what did I get in July 2026", EVIDENCE), (1, ["month 2026-05"]))
