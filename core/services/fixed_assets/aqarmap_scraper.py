"""
Aqarmap EGP/sqm scraper for Cairo districts.

Strategy order:
  1. cloudscraper  — HTTP-level Cloudflare bypass (fast, no browser)
  2. Playwright    — headless Chromium with stealth flags (slow, last resort)
  3. Baseline      — hardcoded 2024/2025 Cairo market midpoints (always works)

The returned map is ALWAYS valid — the caller never needs to check for None.
source field values:
  "aqarmap_live+baseline"  → live data merged with baseline gaps
  "baseline_only"          → scraping failed or was skipped
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
# Baseline — 2024/2025 Cairo market midpoints (EGP / sqm)
# Keys match LOCATION_ALIASES in property_valuation_service.py
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
    "Shorouk": 30_000,
    "Madinaty": 38_000,
    "6th of October": 27_000,
    "Mokattam": 27_000,
    "Badr City": 22_000,
    "Shubra": 22_000,
    "Obour": 20_000,
    "Boulaq": 20_000,
    "Hadayek el Kobba": 28_000,
    "Abbassia": 24_000,
    "Ain Shams": 18_000,
    "Imbaba": 18_000,
    "Matariya": 16_000,
    "Helwan": 12_000,
    "Wadi Hof": 14_000,
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

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

_API_HEADERS = {
    **_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
}

# Minimum valid EGP/sqm range
_MIN_RATE = 3_000
_MAX_RATE = 500_000


def _parse_price(raw: str) -> Optional[float]:
    """Extract a numeric EGP/sqm value from a string."""
    digits = re.sub(r"[^\d.]", "", str(raw).replace(",", ""))
    try:
        val = float(digits)
        if 1 <= val < 1_000:      # shown in thousands
            val *= 1_000
        if _MIN_RATE <= val <= _MAX_RATE:
            return round(val, 0)
    except ValueError:
        pass
    return None


def _extract_from_json_blob(data, out: dict) -> None:
    """Recursively hunt for {name/area/district, price_per_sqm/avg_price} pairs."""
    if isinstance(data, dict):
        name = data.get("name") or data.get("area") or data.get("district") or data.get("location_name")
        price_raw = (
            data.get("price_per_sqm")
            or data.get("avg_price_per_sqm")
            or data.get("average_price_per_sqm")
            or data.get("avg_price")
            or data.get("average_price")
            or data.get("price_per_meter")
        )
        if name and price_raw:
            price = _parse_price(str(price_raw))
            if price:
                out[str(name).strip()] = price
        for v in data.values():
            _extract_from_json_blob(v, out)
    elif isinstance(data, list):
        for item in data:
            _extract_from_json_blob(item, out)


# ---------------------------------------------------------------------------
# Strategy 1: cloudscraper (HTTP-level, Cloudflare bypass)
# ---------------------------------------------------------------------------
def _scrape_via_cloudscraper(timeout: int = 20) -> Optional[dict[str, float]]:
    try:
        import cloudscraper
    except ImportError:
        logger.warning("cloudscraper not installed — skipping HTTP strategy")
        return None

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("beautifulsoup4 not installed — skipping HTTP strategy")
        return None

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    results: dict[str, float] = {}

    # --- Try JSON API endpoints first ---
    api_endpoints = [
        "https://aqarmap.com/api/v3/lookup/location/?parent_slug=cairo&lang=en",
        "https://aqarmap.com/api/v3/price-index/?location=cairo&lang=en",
        "https://aqarmap.com/api/v3/location-stats/?slug=cairo",
    ]
    for url in api_endpoints:
        try:
            r = scraper.get(url, headers=_API_HEADERS, timeout=timeout)
            if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
                data = r.json()
                _extract_from_json_blob(data, results)
                if results:
                    logger.info("cloudscraper API hit: %s → %d districts", url, len(results))
                    return results
        except Exception as exc:
            logger.debug("cloudscraper API %s: %s", url, exc)

    # --- Try HTML pages ---
    html_pages = [
        "https://aqarmap.com/en/cairo/",
        "https://aqarmap.com/en/for-sale/cairo/",
        "https://aqarmap.com/ar/cairo/",
    ]
    for url in html_pages:
        try:
            r = scraper.get(url, headers=_HEADERS, timeout=timeout)
            if r.status_code != 200:
                logger.debug("cloudscraper HTML %s → %d", url, r.status_code)
                continue

            html = r.text
            logger.debug("cloudscraper HTML %s → %d bytes", url, len(html))

            # Strategy A: __NEXT_DATA__ (Next.js SSR JSON blob)
            match = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    _extract_from_json_blob(data, results)
                    if results:
                        logger.info("cloudscraper __NEXT_DATA__ → %d districts", len(results))
                        return results
                except Exception:
                    pass

            # Strategy B: application/json script tags
            for block in re.findall(
                r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL
            ):
                try:
                    _extract_from_json_blob(json.loads(block), results)
                except Exception:
                    pass
            if results:
                logger.info("cloudscraper JSON blocks → %d districts", len(results))
                return results

            # Strategy C: BeautifulSoup structural parsing
            soup = BeautifulSoup(html, "html.parser")

            # Cards with district name + price
            for card in soup.select("[class*='area'], [class*='district'], [class*='location'], [class*='neighborhood']"):
                name_el = card.select_one("h2, h3, h4, [class*='name'], [class*='title']")
                price_el = card.select_one("[class*='price'], [class*='sqm'], [class*='meter'], [class*='rate']")
                if name_el and price_el:
                    price = _parse_price(price_el.get_text())
                    if price:
                        results[name_el.get_text(strip=True)] = price

            # Table rows
            if not results:
                for row in soup.select("table tr"):
                    cells = row.select("td")
                    if len(cells) >= 2:
                        price = _parse_price(cells[-1].get_text())
                        if price:
                            results[cells[0].get_text(strip=True)] = price

            if results:
                logger.info("cloudscraper BeautifulSoup → %d districts", len(results))
                return results

        except Exception as exc:
            logger.debug("cloudscraper HTML %s: %s", url, exc)

    return None if not results else results


# ---------------------------------------------------------------------------
# Strategy 2: Playwright headless (last resort)
# ---------------------------------------------------------------------------
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1366,768",
    "--lang=en-US,en",
]


def _scrape_via_playwright(timeout_ms: int = 25_000) -> Optional[dict[str, float]]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.warning("Playwright not installed — skipping browser strategy")
        return None

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    results: dict[str, float] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=_STEALTH_ARGS)
        ctx = browser.new_context(
            user_agent=_HEADERS["User-Agent"],
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = ctx.new_page()

        for url in ["https://aqarmap.com/en/cairo/", "https://aqarmap.com/en/for-sale/cairo/"]:
            try:
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                time.sleep(random.uniform(2, 4))

                html = page.content()
                logger.debug("Playwright %s → %d bytes", url, len(html))

                # __NEXT_DATA__
                match = re.search(
                    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                    html, re.DOTALL
                )
                if match:
                    try:
                        _extract_from_json_blob(json.loads(match.group(1)), results)
                    except Exception:
                        pass

                # JSON blocks
                for block in re.findall(
                    r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
                    html, re.DOTALL
                ):
                    try:
                        _extract_from_json_blob(json.loads(block), results)
                    except Exception:
                        pass

                # BeautifulSoup fallback
                if not results:
                    soup = BeautifulSoup(html, "html.parser")
                    for card in soup.select("[class*='area'], [class*='district'], [class*='location']"):
                        name_el = card.select_one("h2,h3,h4,[class*='name'],[class*='title']")
                        price_el = card.select_one("[class*='price'],[class*='sqm'],[class*='meter']")
                        if name_el and price_el:
                            price = _parse_price(price_el.get_text())
                            if price:
                                results[name_el.get_text(strip=True)] = price

                if results:
                    logger.info("Playwright → %d districts from %s", len(results), url)
                    break

            except PWTimeout:
                logger.warning("Playwright timeout: %s", url)
            except Exception as exc:
                logger.warning("Playwright error %s: %s", url, exc)

        browser.close()

    return results if results else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_rate_map(timeout_ms: int = 25_000) -> dict:
    """
    Always returns a valid property_valuation_rate_map dict.

    Tries cloudscraper → Playwright → baseline.
    source values:
      'aqarmap_live+baseline'  live Aqarmap data merged with baseline
      'baseline_only'          scraping failed, baseline returned
    """
    scraped: Optional[dict[str, float]] = None
    timeout_secs = max(10, timeout_ms // 1_000)

    # Strategy 1: cloudscraper
    try:
        scraped = _scrape_via_cloudscraper(timeout=timeout_secs)
    except Exception as exc:
        logger.warning("cloudscraper strategy failed: %s", exc)

    # Strategy 2: Playwright (only if cloudscraper found nothing)
    if not scraped:
        try:
            scraped = _scrape_via_playwright(timeout_ms=timeout_ms)
        except Exception as exc:
            logger.warning("Playwright strategy failed: %s", exc)

    # Build final map: baseline first, live data wins (overrides matching keys)
    by_city: dict[str, float] = CAIRO_BASELINE.copy()

    if scraped:
        by_city.update(scraped)
        source = "aqarmap_live+baseline"
    else:
        source = "baseline_only"

    logger.info("Rate map ready — source=%s, districts=%d", source, len(by_city))

    return {
        "by_city": by_city,
        "by_governorate": GOVERNORATE_BASELINE.copy(),
        "default": DEFAULT_RATE,
        "source": source,
    }
