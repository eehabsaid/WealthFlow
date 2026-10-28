"""Gold prices come from the source's live feed: the real refresh code runs inside the disposable Django with the feed answered
locally (the suite never calls the real site), and the new price is read back through the Gold Price screen's API. This module
imports no core.*."""

import json

from tests.modules.e2e_settings import django_exec

_CODE = r'''
import json
from unittest.mock import MagicMock, patch
from core.models import GoldPrice
from core.services.fixed_assets.gold_valuation_service import GoldValuationService

rows = [{"description": "عيار 24", "askValue": 7291, "bidValue": 7268}, {"description": "عيار 22", "askValue": 6690, "bidValue": 6668},
        {"description": "عيار 21", "askValue": 6380, "bidValue": 6360}, {"description": "عيار 18", "askValue": 5469, "bidValue": 5451},
        {"description": "الدولار", "askValue": 55.45, "bidValue": 55.35}, {"description": "الأونصة", "askValue": 4010.5, "bidValue": 4010.0}]
resp = MagicMock()
resp.read.return_value = json.dumps(rows).encode()
resp.__enter__.return_value = resp
before = GoldPrice.objects.count()
with patch("core.integrations.gold_price_api._ur.urlopen", return_value=resp):
    GoldValuationService().refresh_latest_prices()
latest = GoldPrice.objects.order_by("-id").first()
print("GOLD_FEED:" + json.dumps({"added": GoldPrice.objects.count() - before, "sell": float(latest.carat_24k), "buy": float(latest.carat_24k_buy),
                                 "usd": float(latest.usd_to_egp), "oz": float(latest.usd_per_oz)}))
'''


def _run(context, reporter, screenshot_logger):
    raw = next(line for line in django_exec(_CODE).splitlines() if line.startswith("GOLD_FEED:"))
    got = json.loads(raw[len("GOLD_FEED:"):])
    ok = got == {"added": 1, "sell": 7268.0, "buy": 7291.0, "usd": 55.35, "oz": 4010.0}
    context.goto_route("#gold-price")
    shot = screenshot_logger.capture(context.page, "gold_price", "feed", "none", "view", "ok" if ok else "fail")
    reporter.add_step("Gold price refresh saves the live feed's prices (sell figure, USD/EGP, ounce)", "Gold Price", "PASS" if ok else "FAIL", json.dumps(got), screenshot_path=shot)


def test_gold_feed_module(context, reporter, screenshot_logger):
    try:
        _run(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "gold_price", "feed_error", "none", "fail", "fail")
        reporter.add_step("Gold price live feed", "Gold Price", "FAIL", f"Exception: {ex}", screenshot_path=shot)
