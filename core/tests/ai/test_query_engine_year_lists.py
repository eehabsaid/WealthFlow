"""Year lists for the model path and multi-year time phrases: both used to keep only part of what was asked."""

from datetime import date

from django.test import SimpleTestCase, TestCase

from core.models import Company, SalaryEntry
from core.services.ai.query_engine.lexicon import norm
from core.services.ai.query_engine.timespec import parse_time
from core.services.ai.tools.salary_answers import MAX_YEAR_ENTRIES, SALARY_INSTRUCTIONS, add_salary_answers
from . import qe_fixtures as fx


class MultiYearTimeParsingTests(SimpleTestCase):
    """'2025 and 2026' used to keep only the first year, silently dropping the second from lists and exports."""

    def years(self, text):
        months = parse_time(norm(text), date(2026, 10, 12)).months
        return sorted({y for y, _ in months}), len(months)

    def test_year_lists_and_spans(self):
        for text, years in (("salaries for 2025 and 2026", [2025, 2026]), ("salaries 2024, 2025 and 2026", [2024, 2025, 2026]),
                            ("from 2025 to 2026", [2025, 2026]), ("رواتب 2025 و 2026", [2025, 2026]),
                            ("salary 2026", [2026]), ("in 2025", [2025])):
            with self.subTest(text=text):
                got, n = self.years(text)
                self.assertEqual(got, years)
                self.assertEqual(n, 12 * len(years))

    def test_month_ranges_are_untouched(self):
        self.assertEqual(self.years("jun 2026 to sep 2026"), ([2026], 4))
        self.assertEqual(self.years("2026-01 to 2026-03"), ([2026], 3))


class SalaryYearListTests(TestCase):
    """Model path: the salary tool payload carries every entry of a named year (the timeline is capped at 20)."""

    def setUp(self):
        fx.build(self)
        co = Company.objects.get(owner=self.user)
        months = ("February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
        for i, month in enumerate(months):
            SalaryEntry.objects.create(company=co, year=2026, month=month, paid=str(1000 + i), expected="1000")
        beta = Company.objects.create(owner=self.user, name="Beta", display_name="Beta")
        for month in ("January", *months):
            SalaryEntry.objects.create(company=beta, year=2026, month=month, paid="5", expected="5")

    def test_whole_year_is_listed_not_capped_at_20(self):
        res = {"salary": {}}
        add_salary_answers(res, self.user, "list the paid salaries for year 2026")
        entries = res["salary"]["requested_year_entries"]
        self.assertEqual(len(entries), 24)
        self.assertEqual((entries[0]["month"], entries[0]["company"]), ("January", "Acme"))
        self.assertIn("87,643.86", entries[0]["paid_formatted"])

    def test_no_year_no_list_and_owner_scoped(self):
        res = {"salary": {}}
        add_salary_answers(res, self.user, "what is my average salary")
        self.assertNotIn("requested_year_entries", res["salary"])
        other = {"salary": {}}
        add_salary_answers(other, self.other, "salary 2026")
        self.assertEqual(len(other["salary"]["requested_year_entries"]), 1)
        self.assertIn("111.00", other["salary"]["requested_year_entries"][0]["paid_formatted"])

    def test_cap_and_rule_text(self):
        self.assertGreaterEqual(MAX_YEAR_ENTRIES, 100)
        self.assertIn("requested_year_entries", SALARY_INSTRUCTIONS)
