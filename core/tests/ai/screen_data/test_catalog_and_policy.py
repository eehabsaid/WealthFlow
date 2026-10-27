"""The live endpoint catalogue and the rules for what may be offered."""

from __future__ import annotations

from django.test import SimpleTestCase

from core.services.ai.screen_data import catalog, policy, shrink

CASH = "/api/financial-advisor/cash-flow-custom-projection/"


class PolicyTest(SimpleTestCase):
    def test_denied_families_are_never_in_the_catalogue(self):
        paths = [e.path for e in catalog.endpoints()]
        for denied in ("/api/auth/", "/api/users", "/api/roles", "/api/settings/", "/api/billing/", "/api/account/",
                       "/api/financial-advisor/ai/", "/api/ai-platform/", "/api/export/", "/api/reports/", "/api/documents/"):
            self.assertFalse([p for p in paths if p.startswith(denied)], denied)

    def test_endpoints_that_do_something_are_denied_by_their_path(self):
        for path in ("/api/gold/refresh/", "/api/rates/refresh/", "/api/settings/backup/create/", "/api/salary/generate-current/",
                     "/api/recurring-transactions/process-due/", "/api/settings/ai/", "/api/auth/me/"):
            self.assertFalse(policy.allowed(path), path)
        self.assertFalse(policy.allowed("/accounts/login/"))
        self.assertTrue(policy.allowed(CASH))

    def test_every_listed_endpoint_passes_the_policy_and_answers_get(self):
        self.assertGreater(len(catalog.endpoints()), 40)
        for e in catalog.endpoints():
            self.assertTrue(policy.allowed(e.path), e.path)
            self.assertTrue(hasattr(e.callback.view_class, "get"), e.path)

    def test_the_cash_projection_is_listed_with_its_parameters_and_the_screen_that_uses_it(self):
        entry = next(e for e in catalog.endpoints() if e.path == CASH)
        params = dict(entry.params)
        self.assertTrue({"target_date", "currency_scope", "exclude", "days"} <= set(params))
        self.assertIn("base_only", params["currency_scope"])
        self.assertIn("total_liquid", params["currency_scope"])
        self.assertTrue(any("cash_flow" in s for s in entry.screens), entry.screens)
        self.assertIn("cash projection", entry.doc.lower())


class SearchTest(SimpleTestCase):
    def test_a_search_by_the_screens_words_finds_the_endpoint(self):
        for words in ("cash flow projection", "cash projection", "projected cash balance", "custom projection target date"):
            top = [m["path"] for m in catalog.search(words)["matches"]]
            self.assertIn(CASH, top[:3], (words, top))

    def test_search_names_the_parameters(self):
        match = next(m for m in catalog.search("cash flow projection")["matches"] if m["path"] == CASH)
        self.assertIn("target_date", match["query_parameters"])

    def test_other_screens_are_found_too(self):
        self.assertIn("/api/financial-advisor/wealth-growth-forecast/", [m["path"] for m in catalog.search("wealth growth forecast")["matches"]][:3])
        self.assertIn("/api/budgets/alerts/", [m["path"] for m in catalog.search("budget alerts")["matches"]][:3])
        self.assertIn("/api/expenses/summary/", [m["path"] for m in catalog.search("expenses summary")["matches"]][:3])

    def test_an_empty_search_lists_the_groups_and_a_miss_says_so(self):
        groups = catalog.search("")
        self.assertIn("financial-advisor", groups["groups"])
        self.assertGreater(groups["endpoints_total"], 40)
        miss = catalog.search("zzzzqqqq")
        self.assertEqual(miss["matches"], [])
        self.assertIn("note", miss)


class ShrinkTest(SimpleTestCase):
    def test_small_data_is_untouched(self):
        data = {"a": [1, 2, 3], "b": "x"}
        self.assertEqual(shrink.fit(data, 1000), (data, []))

    def test_long_lists_are_cut_and_the_cut_is_reported(self):
        data = {"total": 5, "rows": [{"n": i, "t": "x" * 40} for i in range(500)]}
        fitted, notes = shrink.fit(data, 3000)
        self.assertEqual(fitted["total"], 5)
        self.assertLess(len(fitted["rows"]), 500)
        self.assertTrue(any("of 500" in n for n in notes), notes)

    def test_hopeless_data_returns_an_overview(self):
        fitted, notes = shrink.fit({"k%d" % i: list(range(50)) for i in range(400)}, 500)
        self.assertIn("too_large_overview", fitted)
        self.assertTrue(notes)
