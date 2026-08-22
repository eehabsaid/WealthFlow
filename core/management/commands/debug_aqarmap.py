"""
python manage.py debug_aqarmap

Tries multiple Aqarmap URLs and reports which ones contain price data.
Run this, paste the output so the scraper selectors can be finalised.
"""
from __future__ import annotations
import json
import re
import time
from django.core.management.base import BaseCommand

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

PRICE_KEYS = [
    "price_per_sqm", "avg_price", "average_price", "pricePerMeter",
    "avgPrice", "price_per_meter", "avg_per_meter", "averagePricePerMeter",
    "avgPricePerMeter", "meter_price", "sqm_price",
]

CANDIDATE_URLS = [
    "https://aqarmap.com.eg/en/for-sale/property-type/cairo/",
    "https://aqarmap.com.eg/en/for-sale/property-type/cairo/new-cairo/",
    "https://aqarmap.com.eg/en/for-sale/property-type/cairo/maadi/",
    "https://aqarmap.com.eg/en/neighborhood/",
    "https://aqarmap.com.eg/en/price-guide/",
    "https://index.aqarmap.com/",
    "https://aqarmap.com.eg/api/v3/lookup/location/?parent_slug=cairo&lang=en",
    "https://aqarmap.com.eg/api/v3/location/cairo/stats/",
    "https://aqarmap.com.eg/api/v3/price-index/?location=cairo",
]


def _extract_rsc(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', html, re.DOTALL)
    out = ""
    for c in chunks:
        try:
            out += json.loads(c)
        except Exception:
            pass
    return out


def _signals(html: str) -> dict:
    rsc = _extract_rsc(html)
    combined = html + rsc
    signals = {}
    for k in PRICE_KEYS:
        signals[k] = k in combined
    signals["__NEXT_DATA__"] = "__NEXT_DATA__" in html
    signals["rsc_chunks"] = html.count("__next_f.push")
    signals["topAreasData"] = "topAreasData" in combined
    signals["cloudflare/blocked"] = any(w in html.lower() for w in ["cloudflare", "just a moment", "403 forbidden"])

    # Find any numeric price-looking values near price keys
    price_hits = re.findall(
        r'(?:' + '|'.join(PRICE_KEYS) + r')["\s:]+(\d{4,7})', combined
    )
    signals["price_numbers_found"] = price_hits[:5]
    return signals


class Command(BaseCommand):
    help = "Scan multiple Aqarmap URLs to find where price data lives"

    def handle(self, *args, **options):
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )

        for url in CANDIDATE_URLS:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"URL: {url}")
            try:
                r = scraper.get(url, headers=HEADERS, timeout=20)
                self.stdout.write(f"Status : {r.status_code}  |  Bytes: {len(r.text):,}")
                if r.status_code == 200:
                    signals = _signals(r.text)
                    for k, v in signals.items():
                        self.stdout.write(f"  {k:<35}: {v}")
                    # Save if promising
                    has_price = any(signals.get(k) for k in PRICE_KEYS) or signals["price_numbers_found"]
                    if has_price:
                        fname = url.replace("https://", "").replace("/", "_").strip("_") + ".html"
                        with open(fname, "w", encoding="utf-8") as f:
                            f.write(r.text)
                        self.stdout.write(self.style.SUCCESS(f"  *** PRICE DATA FOUND — saved to {fname}"))
                else:
                    self.stdout.write(f"  Response: {r.text[:200]}")
            except Exception as exc:
                self.stdout.write(f"  ERROR: {exc}")
            time.sleep(1)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Done. Paste this output back to fix the scraper.")
