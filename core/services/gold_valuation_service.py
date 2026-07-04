from __future__ import annotations

import re
from dataclasses import dataclass

from django.db import transaction

from core.models import GoldPrice, GoldPriceHistory


@dataclass
class GoldPriceRefreshResult:
    saved: int = 0
    source_gold: str = "goldbullioneg.com"
    source_fx: str = "goldbullioneg.com"

    def to_dict(self):
        return {"saved": self.saved, "source_gold": self.source_gold, "source_fx": self.source_fx}


class GoldValuationService:
    def refresh_latest_prices(self):
        import ssl as _ssl
        import urllib.request as _ur
        from html.parser import HTMLParser

        class GoldTableParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_table = False
                self.in_tr = False
                self.in_td = False
                self.current_cell = None
                self.current_row = []
                self.rows = []

            def handle_starttag(self, tag, attrs):
                if tag == "table" and not self.in_table:
                    self.in_table = True
                    return
                if not self.in_table:
                    return
                if tag == "tr":
                    self.in_tr = True
                    self.current_row = []
                elif self.in_tr and tag == "td":
                    self.in_td = True
                    self.current_cell = {"text": "", "data_val": None}
                    attrs = dict(attrs)
                    if "data-val" in attrs:
                        self.current_cell["data_val"] = attrs["data-val"]

            def handle_data(self, data):
                if self.in_td and self.current_cell is not None:
                    self.current_cell["text"] += data

            def handle_endtag(self, tag):
                if tag == "td" and self.in_td:
                    self.current_row.append(self.current_cell)
                    self.in_td = False
                    self.current_cell = None
                elif tag == "tr" and self.in_tr:
                    if self.current_row:
                        self.rows.append(self.current_row)
                    self.in_tr = False
                elif tag == "table" and self.in_table:
                    self.in_table = False

        # Keep parity with the previously working refresh source/parser.
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE

        page_url = "https://goldbullioneg.com/%D8%A3%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/"
        req = _ur.Request(page_url, headers={"User-Agent": "SalaryTracker/1.0"})
        with _ur.urlopen(req, timeout=15, context=ctx) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")

        parser = GoldTableParser()
        parser.feed(page_html)

        if not parser.rows or len(parser.rows) < 8:
            raise ValueError("Unable to parse complete gold price table from goldbullioneg.com")

        prices_egp: dict[int, dict[str, float]] = {}
        usd_to_egp = None
        usd_per_oz = None

        for row in parser.rows:
            if len(row) < 3:
                continue
            label = (row[0].get("text") or "").strip()
            buy_val = (row[1].get("data_val") or row[1].get("text") or "").strip()
            sell_val = (row[2].get("data_val") or row[2].get("text") or "").strip()

            if not buy_val or not sell_val:
                continue

            try:
                buy_num = float(str(buy_val).replace(",", ""))
                sell_num = float(str(sell_val).replace(",", ""))
            except ValueError:
                continue

            karat_match = re.search(r"عيار\s*([0-9]{1,2})", label)
            if karat_match:
                carat = int(karat_match.group(1))
                prices_egp[carat] = {"buy": buy_num, "sell": sell_num}
                continue

            label_lower = label.lower()
            if "دولار" in label_lower:
                usd_to_egp = sell_num
                continue

            if "أونصة" in label_lower or "ounce" in label_lower:
                usd_per_oz = sell_num

        if not all(carat in prices_egp for carat in (24, 22, 21, 18)):
            raise ValueError("Missing required karat prices from goldbullioneg.com")

        if usd_to_egp is None:
            raise ValueError("Could not find USD/EGP rate on goldbullioneg.com")

        if usd_per_oz is None:
            raise ValueError("Could not find USD/oz spot price on goldbullioneg.com")

        usd_gram_24k = prices_egp[24]["sell"] / usd_to_egp if usd_to_egp else 0

        saved_price = {
            "carat_24k": round(prices_egp[24]["sell"], 2),
            "carat_22k": round(prices_egp[22]["sell"], 2),
            "carat_21k": round(prices_egp[21]["sell"], 2),
            "carat_18k": round(prices_egp[18]["sell"], 2),
            "carat_24k_buy": round(prices_egp[24]["buy"], 2),
            "carat_22k_buy": round(prices_egp[22]["buy"], 2),
            "carat_21k_buy": round(prices_egp[21]["buy"], 2),
            "carat_18k_buy": round(prices_egp[18]["buy"], 2),
            "usd_gram_24k": round(usd_gram_24k, 6),
            "usd_per_oz": round(usd_per_oz, 4),
            "usd_to_egp": round(usd_to_egp, 6),
            "source_gold": "goldbullioneg.com",
            "source_fx": "goldbullioneg.com",
        }

        with transaction.atomic():
            gp = GoldPrice.objects.create(**saved_price)
            GoldPriceHistory.objects.create(
                carat_24k=gp.carat_24k,
                carat_21k=gp.carat_21k,
                carat_18k=gp.carat_18k,
                usd_gram_24k=gp.usd_gram_24k,
                usd_per_oz=gp.usd_per_oz,
                usd_to_egp=gp.usd_to_egp,
            )

        from core.views import _refresh_all_gold_assets_from_live_prices

        _refresh_all_gold_assets_from_live_prices()

        return GoldPriceRefreshResult(saved=1)
