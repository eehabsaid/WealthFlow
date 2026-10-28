"""Gold prices come from the site's live feed (its HTML table can stay on old numbers); the feed's sell figure is the one stored."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from core.integrations.gold_price_api import fetch_latest_gold_prices, parse_price_feed
from core.models import GoldPrice
from core.services.fixed_assets.gold_valuation_service import GoldValuationService

FEED = [
    {"id": 1, "description": "عيار 24", "askValue": 7291, "bidValue": 7268, "is_hidden": ""},
    {"id": 2, "description": "عيار 22", "askValue": "6,690", "bidValue": "6,668"},
    {"id": 3, "description": "عيار 21", "askValue": 6380, "bidValue": 6360},
    {"id": 4, "description": "عيار 18", "askValue": 5469, "bidValue": 5451},
    {"id": 5, "description": "الدولار", "askValue": 55.45, "bidValue": 55.35},
    {"id": 6, "description": "الأونصة", "askValue": 4010.5, "bidValue": 4010.0},
    {"id": 7, "description": "الجنيه الذهب", "askValue": 51040, "bidValue": 50880},
    {"id": 8, "description": "عيار 14", "askValue": 0, "bidValue": 0},
]


def response(rows):
    resp = MagicMock()
    resp.read.return_value = json.dumps(rows).encode()
    resp.__enter__.return_value = resp
    return resp


class FeedParseTests(SimpleTestCase):
    def test_karats_dollar_and_ounce_are_read(self):
        prices, usd, oz = parse_price_feed(FEED)
        self.assertEqual(prices[24], {"buy": 7291.0, "sell": 7268.0})
        self.assertEqual(prices[22]["sell"], 6668.0)
        self.assertEqual((usd, oz), (55.35, 4010.0))
        self.assertNotIn(14, prices)   # a zero row is skipped

    def test_garbage_rows_are_ignored(self):
        self.assertEqual(parse_price_feed({"not": "a list"}), ({}, None, None))
        self.assertEqual(parse_price_feed(["x", {"description": "عيار 24", "askValue": "n/a", "bidValue": None}]), ({}, None, None))


class FeedFetchTests(SimpleTestCase):
    def test_fetch_uses_the_feed_sell_figures(self):
        with patch("core.integrations.gold_price_api._ur.urlopen", return_value=response(FEED)) as opened:
            data = fetch_latest_gold_prices()
        self.assertIn("/wp-json/gbs/prices", opened.call_args[0][0].full_url)
        self.assertEqual(data["prices_egp"][24], {"buy": 7291.0, "sell": 7268.0})
        self.assertEqual((data["usd_to_egp"], data["usd_per_oz"]), (55.35, 4010.0))

    def test_missing_karat_is_an_error_not_a_stale_save(self):
        with patch("core.integrations.gold_price_api._ur.urlopen", return_value=response(FEED[1:])):
            with self.assertRaises(ValueError):
                fetch_latest_gold_prices()

    def test_table_is_used_only_for_missing_dollar_and_ounce(self):
        table = {"prices_egp": {}, "usd_to_egp": 55.25, "usd_per_oz": 3997.64}
        rows = [r for r in FEED if r["id"] not in (5, 6)]
        with patch("core.integrations.gold_price_api._ur.urlopen", return_value=response(rows)), \
                patch("core.integrations.gold_price_api.fetch_gold_table_prices", return_value=table) as fallback:
            with self.assertLogs("core.integrations.gold_price_api", "WARNING"):
                data = fetch_latest_gold_prices()
        fallback.assert_called_once()
        self.assertEqual(data["prices_egp"][24]["sell"], 7268.0)   # still from the feed
        self.assertEqual((data["usd_to_egp"], data["usd_per_oz"]), (55.25, 3997.64))


class RefreshSavesFeedPriceTests(TestCase):
    def test_refresh_saves_the_new_price(self):
        with patch("core.integrations.gold_price_api._ur.urlopen", return_value=response(FEED)):
            GoldValuationService().refresh_latest_prices()
        latest = GoldPrice.objects.order_by("-id").first()
        self.assertEqual((float(latest.carat_24k), float(latest.carat_24k_buy)), (7268.0, 7291.0))
