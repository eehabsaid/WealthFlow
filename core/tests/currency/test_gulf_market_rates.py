"""Gulf market tests: rates, gold and Excel export."""


import io
from decimal import Decimal
from types import SimpleNamespace

from openpyxl import load_workbook

from core.models import BalanceEntry, Currency, ExchangeRate
from core.services.fixed_assets.gold_sync_service.sync import _refresh_gold_asset_pricing
from core.services.shared.market_profile import spot_gold_snapshot
from .gulf_market_support import GulfMarketBase, RATES


class RatesAndGoldTests(GulfMarketBase):
    def setUp(self):
        super().setUp()
        ExchangeRate.objects.create(
            currency_code="EGP", currency_name="Egyptian Pound", buy_rate=Decimal("0.019"),
            sell_rate=Decimal("0.019"), mid_rate=Decimal("0.019"),
        )

    def _rate_codes(self):
        return {r["currency_code"] for r in self.client.get("/api/rates/").json()["rates"]}

    def test_egyptian_user_still_sees_egp_rate(self):
        self.assertIn("EGP", self._rate_codes())

    def test_gulf_user_does_not_see_egp_rate_but_sees_aed(self):
        self.switch("SAR")
        codes = self._rate_codes()
        self.assertNotIn("EGP", codes)
        self.assertIn("AED", codes)

    def test_gulf_gold_is_spot_in_base_currency(self):
        self.switch("SAR")
        gold = self.client.get("/api/gold/").json()["gold"]
        self.assertEqual(gold["market"], "spot")
        self.assertEqual(gold["currency"], "SAR")
        expected_rate = float(Decimal(RATES["USD"]) / Decimal(RATES["SAR"]))  # SAR per 1 USD
        self.assertAlmostEqual(gold["usd_to_base"], expected_rate, places=3)
        self.assertAlmostEqual(gold["carat_24k"], 134 * expected_rate, places=1)
        self.assertAlmostEqual(gold["carat_22k"], 134 * expected_rate * 22 / 24, places=1)
        self.assertEqual(gold["carat_24k_buy"], gold["carat_24k"])

    def test_egyptian_gold_is_unchanged_dealer_price(self):
        gold = self.client.get("/api/gold/").json()["gold"]
        self.assertNotIn("market", gold)
        self.assertEqual(gold["currency"], "EGP")
        self.assertEqual(gold["carat_24k"], 7000)

    def test_gold_refresh_view_also_returns_user_scoped_prices(self):
        self.switch("AED")
        from core.views.settings.market import gold_price_views as views
        data = views._gold_for_user(self.user, self.gold)
        self.assertEqual(data["currency"], "AED")

    def test_asset_sync_values_gulf_gold_in_base_not_egp(self):
        self.switch("SAR")
        snap = spot_gold_snapshot(self.user, self.gold)
        details = SimpleNamespace(
            purity="21k", unit="gram", weight=Decimal("10"), market_price=0, cashback_per_gram=0,
            save=lambda **kw: None,
        )
        asset = SimpleNamespace(
            owner=self.user, asset_type="Gold", purchase_price=Decimal("3750"),
            purchase_usd_rate=0, purchase_price_usd=0, current_market_value=0,
            valuation_source="", last_valuation_date=None, save=lambda **kw: None,
        )
        _refresh_gold_asset_pricing(asset, gold_details=details, latest_gold_price=self.gold)
        self.assertAlmostEqual(float(asset.current_market_value), snap["carat_21k"] * 10, places=1)
        self.assertAlmostEqual(float(asset.purchase_usd_rate), snap["usd_to_base"], places=4)
        self.assertAlmostEqual(float(asset.purchase_price_usd), 3750 / snap["usd_to_base"], places=2)


class ExcelExportGulfTests(GulfMarketBase):
    def _workbook(self):
        response = self.client.get("/api/export/excel/")
        self.assertEqual(response.status_code, 200, response.content[:300])
        return load_workbook(io.BytesIO(b"".join(response.streaming_content) if response.streaming else response.content))

    def _texts(self, wb):
        out = []
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        out.append(str(cell.value))
                    out.append(cell.number_format)
        return out

    def _seed_balances(self, home_codes):
        for code in home_codes:
            cur = Currency.objects.get(owner=self.user, code=code)
            BalanceEntry.objects.create(owner=self.user, title="Home Balance", currency=cur, amount=100)

    def test_sar_user_workbook_has_no_egp_and_no_duplicate_columns(self):
        self.switch("SAR")
        self._seed_balances(["SAR", "USD"])
        wb = self._workbook()
        bad = [t for t in self._texts(wb) if "EGP" in t or "ج.م" in t or "الجنيه الذهب" in t]
        self.assertEqual(bad, [])
        header = [c.value for c in wb["BALANCE"][1]][:6]
        self.assertEqual(header[1:5], ["SAR", "USD", "EUR", "AED"])
        total = str(wb["BALANCE"].cell(row=wb["BALANCE"].max_row, column=2).value)
        formulas = [str(c.value) for row in wb["BALANCE"].iter_rows() for c in row if str(c.value).startswith("=B")]
        self.assertTrue(formulas)
        self.assertTrue(all("'Exchange Rates'!" not in f for f in formulas), total)

    def test_usd_user_has_no_duplicate_usd_column(self):
        self.switch("USD")
        wb = self._workbook()
        header = [c.value for c in wb["BALANCE"][1]][1:5]
        self.assertEqual(header[0], "USD")
        self.assertEqual(header.count("USD"), 1)

    def test_egyptian_user_layout_unchanged(self):
        wb = self._workbook()
        header = [c.value for c in wb["BALANCE"][1]][:6]
        self.assertEqual(header, ["Title", "EGP", "USD", "EUR", "SAR", "Gold"])
