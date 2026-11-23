"""The scraped rate map reaches every stored copy; renamed Aqarmap slugs fall back to their alternatives (no network)."""

import json
import sys
import types
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from core.models import AppSettings
from core.services.fixed_assets.aqarmap_scraper import rate_map_is_current, save_rate_map
from core.services.fixed_assets.aqarmap_scraper.constants import DISTRICT_PATHS
from core.services.fixed_assets.aqarmap_scraper.district_scraper import _scrape_districts

KEY = "property_valuation_rate_map"


def _page(slug, price):
    payload = (
        '"averagePriceData":{"location":{"slug":"%s"},'
        '"data":{"1":{"data":{"average_price":[{"value":"%s"}]}}}}' % (slug, price)
    )
    return "self.__next_f.push([1," + json.dumps(payload) + "])"


def _site(pages):
    """A fake cloudscraper whose district pages are {slug: (returned_slug, price)}; any other slug redirects to Cairo."""
    def get(url, **kwargs):
        slug = url.split("/property-type/cairo/")[1].strip("/")
        returned, price = pages.get(slug, ("cairo", 29300))
        return types.SimpleNamespace(status_code=200, text=_page(returned, price))
    return types.SimpleNamespace(create_scraper=lambda **k: types.SimpleNamespace(get=get))


class RenamedSlugTest(SimpleTestCase):
    def _scrape(self, pages):
        with mock.patch.dict(sys.modules, {"cloudscraper": _site(pages)}), mock.patch("time.sleep"):
            return _scrape_districts(timeout=1, diag={})

    def test_maadi_uses_its_new_slug(self):
        self.assertIn("el-maadi", DISTRICT_PATHS)
        self.assertEqual(self._scrape({"el-maadi": ("el-maadi", 61000)})["Maadi"], 61000.0)

    def test_an_alternative_slug_is_tried_when_the_main_one_redirects(self):
        self.assertEqual(self._scrape({"new-cairo/madinaty": ("madinaty", 44000)})["Madinaty"], 44000.0)

    def test_a_nested_slug_is_matched_on_its_last_part(self):
        self.assertEqual(self._scrape({"new-cairo/ltjm-lkhms": ("ltjm-lkhms", 52000)})["Fifth Settlement"], 52000.0)

    def test_the_new_aqarmap_slugs_are_used(self):
        for slug in ("al-zamalek", "el-mohandesen", "al-oubour", "el-matarya", "hadayek-el-koba", "downtown", "downtown/bolak-abo-el-ala"):
            self.assertIn(slug, DISTRICT_PATHS)

    def test_a_district_with_no_working_slug_is_left_out(self):
        self.assertNotIn("Zamalek", self._scrape({"el-maadi": ("el-maadi", 61000)}))

    def test_live_price_is_logged_without_a_format_error(self):
        with self.assertLogs("core.services.fixed_assets.aqarmap_scraper.district_scraper", level="INFO") as logs:
            self._scrape({"el-maadi": ("el-maadi", 61000)})
        self.assertTrue(any("Maadi" in line and "61,000" in line and "[live]" in line for line in logs.output))


class SaveRateMapTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="rate-owner", password="x")
        self.new = {"by_city": {"Zamalek": 1}, "by_governorate": {}, "default": 5, "source": "aqarmap_live+baseline"}

    def test_an_existing_per_user_copy_is_updated_with_the_global_row(self):
        AppSettings.set(KEY, '{"by_city": {"Zamalek": 95000}}')
        AppSettings.set(KEY, '{"by_city": {"Zamalek": 95000}}', user=self.user)
        save_rate_map(self.new)
        for owner in (None, self.user):
            self.assertEqual(json.loads(AppSettings.objects.get(key=KEY, owner=owner).value), self.new)
        self.assertEqual(json.loads(AppSettings.get(KEY, user=self.user)), self.new)

    def test_users_without_a_copy_do_not_get_one(self):
        save_rate_map(self.new)
        self.assertEqual(list(AppSettings.objects.filter(key=KEY).values_list("owner", flat=True)), [None])

    def test_current_check_sees_a_stale_per_user_copy(self):
        save_rate_map(self.new)
        AppSettings.set(KEY, '{"by_city": {"Zamalek": 95000}}', user=self.user)
        self.assertFalse(rate_map_is_current(self.new))
        save_rate_map(self.new)
        self.assertTrue(rate_map_is_current(self.new))

    def test_command_syncs_a_stale_per_user_copy_even_when_the_global_row_is_unchanged(self):
        save_rate_map(self.new)
        AppSettings.set(KEY, '{"by_city": {"Zamalek": 95000}}', user=self.user)
        out = StringIO()
        with mock.patch("core.services.fixed_assets.aqarmap_scraper.build_rate_map", return_value=self.new):
            call_command("scrape_property_rates", stdout=out)
        self.assertEqual(json.loads(AppSettings.objects.get(key=KEY, owner=self.user).value), self.new)
