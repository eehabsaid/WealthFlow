"""When the Aqarmap scrape returns nothing, the Settings toast says why (no network: cloudscraper is faked)."""

import sys
import types
from unittest import mock

from django.test import SimpleTestCase

from core.services.fixed_assets.aqarmap_scraper import build_rate_map
from core.services.fixed_assets.aqarmap_scraper.district_scraper import _scrape_districts


def _fake_cloudscraper(status, text=""):
    resp = types.SimpleNamespace(status_code=status, text=text)
    scraper = types.SimpleNamespace(get=lambda *a, **k: resp)
    return types.SimpleNamespace(create_scraper=lambda **k: scraper)


class ScrapeReasonTest(SimpleTestCase):
    def _run(self, module):
        diag = {}
        with mock.patch.dict(sys.modules, {"cloudscraper": module}), mock.patch("time.sleep"):
            out = _scrape_districts(timeout=1, diag=diag)
        return out, diag

    def test_site_refusal_is_reported_as_blocked(self):
        out, diag = self._run(_fake_cloudscraper(403))
        self.assertEqual((out, diag["reason"]), ({}, "blocked"))

    def test_page_without_price_data_is_reported_as_no_data(self):
        out, diag = self._run(_fake_cloudscraper(200, "<html>nothing here</html>"))
        self.assertEqual((out, diag["reason"]), ({}, "no_data"))

    def test_missing_package_is_reported(self):
        diag = {}
        with mock.patch.dict(sys.modules, {"cloudscraper": None}):
            self.assertEqual(_scrape_districts(timeout=1, diag=diag), {})
        self.assertEqual(diag["reason"], "not_installed")

    def test_build_rate_map_passes_the_reason_and_still_returns_the_baseline(self):
        diag = {}
        with mock.patch.dict(sys.modules, {"cloudscraper": _fake_cloudscraper(429)}), mock.patch("time.sleep"):
            rate_map = build_rate_map(timeout_ms=10_000, diag=diag)
        self.assertEqual(rate_map["source"], "baseline_only")
        self.assertEqual(diag["reason"], "blocked")
        self.assertTrue(rate_map["by_city"])
