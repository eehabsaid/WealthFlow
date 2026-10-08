"""Exchange Rates featured cards: Buy and Sell sit on separate rows so six-decimal
numbers no longer collide (layout only; the values come from the same rateInBase calls)."""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class RatesFeaturedCardLayoutTests(SimpleTestCase):
    def setUp(self):
        self.src = (Path(settings.BASE_DIR) / "static" / "js" / "exchange_rates" / "rates_render.js").read_text(encoding="utf-8")

    def test_buy_and_sell_are_stacked(self):
        self.assertIn('class="rate-card-spread"', self.src)
        self.assertIn("flex-direction:column", self.src)

    def test_values_still_come_from_the_same_rate_fields(self):
        for field in ("buy_rate", "sell_rate", "mid_rate"):
            self.assertIn(f'rateInBase(r.currency_code, "{field}")', self.src)
