"""
Aqarmap EGP/sqm scraper for Cairo districts.

Fetches https://aqarmap.com.eg/en/for-sale/property-type/cairo/{slug}/
for each known district, parses the Next.js RSC payload, and extracts
averagePriceData → latest apartment price per sqm.

KEY VALIDATION: the returned averagePriceData.location.slug must end
with the requested slug. If it doesn't, Aqarmap redirected to the
city-wide page (returning the Cairo default ~27,100) — that value is
discarded and baseline is used instead.

source values:
  "aqarmap_live+baseline"  → live data merged with baseline gaps
  "baseline_only"          → scraping failed or skipped
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# District slug → display name
# Names must align with LOCATION_ALIASES in property_valuation_service.py
# ---------------------------------------------------------------------------
DISTRICT_SLUGS: dict[str, str] = {
    "zamalek": "Zamalek",
    "garden-city": "Garden City",
    "maadi": "Maadi",
    "heliopolis": "Heliopolis",
    "nasr-city": "Nasr City",
    "new-cairo": "New Cairo",
    "dokki": "Dokki",
    "mohandessin": "Mohandessin",
    "6th-of-october": "6th of October",
    "el-sheikh-zayed-city": "Sheikh Zayed",
    "new-administrative-capital": "New Administrative Capital",
    "mokattam": "Mokattam",
    "helwan": "Helwan",
    "shubra": "Shubra",
    "ain-shams": "Ain Shams",
    "hadayek-el-kobba": "Hadayek el Kobba",
    "abbassia": "Abbassia",
    "downtown-cairo": "Downtown Cairo",
    "madinaty": "Madinaty",
    "el-shorouk": "Shorouk",
    "badr-city": "Badr City",
    "el-obour": "Obour",
    "agouza": "Agouza",
    "imbaba": "Imbaba",
    "el-matariya": "Matariya",
    "boulaq": "Boulaq",
    "wadi-hof": "Wadi Hof",
}

BASE_URL = "https://aqarmap.com.eg/en/for-sale/property-type/cairo/{slug}/"

# ---------------------------------------------------------------------------
# Baseline — used for missing/invalid districts
# ---------------------------------------------------------------------------
CAIRO_BASELINE: dict[str, float] = {
    "Zamalek": 95_000,
    "Garden City": 75_000,
    "Maadi": 55_000,
    "Heliopolis": 52_000,
    "Dokki": 52_000,
    "Mohandessin": 52_000,
    "Fifth Settlement": 48_000,
    "Agouza": 48_000,
    "New Cairo": 45_000,
    "New Administrative Capital": 40_000,
    "Sheikh Zayed": 35_000,
    "Downtown Cairo": 35_000,
    "Nasr City": 32_000,
    "Madinaty": 38_000,
    "Shorouk": 30_000,
    "6th of October": 27_000,
    "Mokattam": 27_000,
    "Hadayek el Kobba": 28_000,
    "Abbassia": 24_000,
    "Badr City": 22_000,
    "Shubra": 22_000,
    "Obour": 20_000,
    "Boulaq": 20_000,
    "Ain Shams": 18_000,
    "Imbaba": 18_000,
    "Matariya": 16_000,
    "Wadi Hof": 22_000,
    "Helwan": 22_000,
}

GOVERNORATE_BASELINE: dict[str, float] = {
    "Cairo": 35_000,
    "Giza": 28_000,
    "Alexandria": 25_000,
    "North Coast": 30_000,
    "Sharm El Sheikh": 40_000,
    "Hurghada": 22_000,
    "Mansoura": 12_000,
    "Tanta": 10_000,
    "Port Said": 14_000,
    "Ismailia": 12_000,
    "Suez": 11_000,
    "Luxor": 9_000,
    "Aswan": 8_000,
    "New Valley": 7_000,
}

DEFAULT_RATE: float = 20_000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

_MIN_RATE = 3_000
_MAX_RATE = 500_000


# ---------------------------------------------------------------------------
# RSC helpers
# ---------------------------------------------------------------------------
def _decode_rsc(html: str) -> str:
    """Concatenate all self.__next_f.push([1, '...']) payloads."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', html, re.DOTALL)
    out = ""
    for c in chunks:
        try:
            out += json.loads(c)
        except Exception:
            pass
    return out


def _extract_avg_price_data(rsc_text: str) -> Optional[dict]:
    """Extract the averagePriceData JSON object from RSC text."""
    idx = rsc_text.find('"averagePriceData"')
    if idx < 0:
        return None
    brace_start = rsc_text.find('{', idx)
    if brace_start < 0:
        return None
    depth = 0
    for i, ch in enumerate(rsc_text[brace_start:], brace_start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(rsc_text[brace_start:i + 1])
                except Exception:
                    return None
    return None


def _latest_apartment_price(avg_data: dict) -> Optional[float]:
    """Return the most recent valid apartment (type '1') price per sqm."""
    try:
        entries = avg_data["data"]["1"]["data"]["average_price"]
        valid = [
            float(e["value"])
            for e in entries
            if _MIN_RATE <= float(e["value"]) <= _MAX_RATE
        ]
        return valid[-1] if valid else None
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def _slug_matches(avg_data: dict, requested_slug: str) -> bool:
    """
    Validate that Aqarmap returned data for the district we requested,
    not a redirect to the city-wide page.

    When a slug doesn't exist, Aqarmap silently redirects to the main
    Cairo page whose averagePriceData.location.slug == "cairo".
    We reject that and fall back to baseline for that district.
    """
    returned_slug = avg_data.get("location", {}).get("slug", "")
    return returned_slug.endswith(requested_slug)


# ---------------------------------------------------------------------------
# Main scraper
# ---------------------------------------------------------------------------
def _scrape_districts(timeout: int = 20) -> dict[str, float]:
    """
    Fetch each district page, validate slug, return {name: price_per_sqm}.
    Districts that redirect to the city default are skipped (baseline used).
    """
    try:
        import cloudscraper
    except ImportError:
        logger.warning("cloudscraper not installed — scraping skipped")
        return {}

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    results: dict[str, float] = {}

    for slug, name in DISTRICT_SLUGS.items():
        url = BASE_URL.format(slug=slug)
        try:
            r = scraper.get(url, headers=_HEADERS, timeout=timeout)
            if r.status_code != 200:
                logger.debug("%-25s HTTP %d — using baseline", slug, r.status_code)
                continue

            rsc = _decode_rsc(r.text)
            avg_data = _extract_avg_price_data(rsc)

            if not avg_data:
                logger.debug("%-25s no averagePriceData — using baseline", slug)
                continue

            if not _slug_matches(avg_data, slug):
                returned = avg_data.get("location", {}).get("slug", "?")
                logger.info(
                    "%-25s slug mismatch (got '%s') — redirect detected, using baseline",
                    slug, returned,
                )
                continue

            price = _latest_apartment_price(avg_data)
            if price:
                results[name] = price
                logger.info("%-30s %10,.0f EGP/sqm  [live]", name, price)
            else:
                logger.debug("%-25s no valid price entries — using baseline", slug)

        except Exception as exc:
            logger.warning("%-25s error: %s — using baseline", slug, exc)

        time.sleep(random.uniform(0.5, 1.2))

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_rate_map(timeout_ms: int = 25_000) -> dict:
    """
    Always returns a valid property_valuation_rate_map dict.
    Baseline fills any district not returned by the live scrape.
    """
    timeout_secs = max(10, timeout_ms // 1_000)

    scraped: dict[str, float] = {}
    try:
        scraped = _scrape_districts(timeout=timeout_secs)
    except Exception as exc:
        logger.warning("Scraping failed entirely: %s", exc)

    # Baseline first, live data overrides only validated districts
    by_city: dict[str, float] = CAIRO_BASELINE.copy()

    if scraped:
        by_city.update(scraped)
        source = "aqarmap_live+baseline"
        logger.info(
            "Rate map: %d live + %d baseline-only = %d total",
            len(scraped), len(by_city) - len(scraped), len(by_city),
        )
    else:
        source = "baseline_only"
        logger.info("Rate map: baseline only (%d districts)", len(by_city))

    return {
        "by_city": by_city,
        "by_governorate": GOVERNORATE_BASELINE.copy(),
        "default": DEFAULT_RATE,
        "source": source,
    }
