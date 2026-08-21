"""
Aqarmap price-per-sqm scraper for Cairo districts.

Tries live scraping first; falls back to a hardcoded baseline map
so the command never silently fails.
"""
from __future__ import annotations

import json
import logging
import random
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Baseline fallback — 2024/2025 Cairo market midpoints (EGP / sqm)
# ---------------------------------------------------------------------------
CAIRO_BASELINE: dict[str, float] = {
    "Zamalek": 95_000,
    "Maadi": 55_000,
    "Heliopolis": 52_000,
    "Nasr City": 32_000,
    "New Cairo": 45_000,
    "Fifth Settlement": 48_000,
    "Dokki": 52_000,
    "Mohandessin": 52_000,
    "6th of October": 27_000,
    "Sheikh Zayed": 35_000,
    "New Administrative Capital": 40_000,
    "Mokattam": 27_000,
    "Helwan": 12_000,
    "Shubra": 22_000,
    "Ain Shams": 18_000,
    "Matariya": 16_000,
    "Hadayek el Kobba": 28_000,
    "Abbassia": 24_000,
    "Garden City": 75_000,
    "Downtown Cairo": 35_000,
    "Boulaq": 20_000,
    "Imbaba": 18_000,
    "Agouza": 48_000,
    "Wadi Hof": 14_000,
    "Badr City": 22_000,
    "Shorouk": 30_000,
    "Madinaty": 38_000,
    "Obour": 20_000,
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
# Scraper
# ---------------------------------------------------------------------------
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-gpu",
    "--window-size=1366,768",
    "--lang=en-US,en",
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Aqarmap price-guide URLs to attempt (most-to-least useful)
_AQARMAP_URLS = [
    "https://aqarmap.com/en/cairo/",
    "https://aqarmap.com/ar/cairo/",
]


def _jitter(lo: float = 1.0, hi: float = 3.0) -> None:
    time.sleep(random.uniform(lo, hi))


def _parse_price(raw: str) -> Optional[float]:
    """Extract a numeric EGP/sqm value from a string."""
    import re
    digits = re.sub(r"[^\d.]", "", raw.replace(",", ""))
    try:
        val = float(digits)
        # Aqarmap often shows price in thousands — normalise obvious low values
        if 1 <= val < 1_000:
            val *= 1_000
        # Sanity gate: 3 000 – 500 000 EGP/sqm
        if 3_000 <= val <= 500_000:
            return round(val, 0)
    except ValueError:
        pass
    return None


def scrape_aqarmap(timeout_ms: int = 25_000) -> Optional[dict]:
    """
    Attempt to scrape Aqarmap for district-level EGP/sqm data.

    Returns dict like::

        {
            "by_city": {"Maadi": 55000, ...},
            "by_governorate": {"Cairo": 35000, ...},
            "default": 20000
        }

    Returns None if scraping fails entirely (caller should fall back to baseline).
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.warning("Playwright not installed — scraping skipped.")
        return None

    results: dict[str, float] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=_STEALTH_ARGS,
        )
        ctx = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        # Mask webdriver property
        ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = ctx.new_page()

        for url in _AQARMAP_URLS:
            try:
                logger.info("Scraping %s", url)
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                _jitter(2, 4)

                # Dismiss any cookie/gdpr banner
                for btn_sel in [
                    "button[id*='accept']",
                    "button[class*='accept']",
                    "button[class*='cookie']",
                    "[data-testid='cookie-accept']",
                ]:
                    try:
                        btn = page.query_selector(btn_sel)
                        if btn and btn.is_visible():
                            btn.click()
                            _jitter(0.5, 1.0)
                            break
                    except Exception:
                        pass

                # Strategy 1: structured price-card elements
                cards = page.query_selector_all(
                    "[class*='area'], [class*='district'], [class*='neighborhood'], "
                    "[class*='location'], [class*='region']"
                )
                for card in cards:
                    try:
                        name_el = card.query_selector(
                            "h2, h3, h4, [class*='name'], [class*='title']"
                        )
                        price_el = card.query_selector(
                            "[class*='price'], [class*='sqm'], [class*='meter'], "
                            "[class*='rate'], [class*='average']"
                        )
                        if not (name_el and price_el):
                            continue
                        name = (name_el.inner_text() or "").strip()
                        price = _parse_price(price_el.inner_text() or "")
                        if name and price:
                            results[name] = price
                    except Exception:
                        continue

                # Strategy 2: table rows
                if not results:
                    rows = page.query_selector_all("table tr")
                    for row in rows:
                        cells = row.query_selector_all("td")
                        if len(cells) >= 2:
                            name = (cells[0].inner_text() or "").strip()
                            price = _parse_price(cells[-1].inner_text() or "")
                            if name and price:
                                results[name] = price

                # Strategy 3: JSON-LD / next-data
                if not results:
                    import re
                    html = page.content()
                    json_blocks = re.findall(
                        r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
                        html, re.DOTALL
                    )
                    for block in json_blocks:
                        try:
                            data = json.loads(block)
                            _extract_from_json(data, results)
                        except Exception:
                            continue

                if results:
                    logger.info("Scraped %d districts from %s", len(results), url)
                    break

            except PWTimeout:
                logger.warning("Timeout on %s", url)
            except Exception as exc:
                logger.warning("Error scraping %s: %s", url, exc)

        browser.close()

    if not results:
        return None

    return {
        "by_city": results,
        "by_governorate": GOVERNORATE_BASELINE.copy(),
        "default": DEFAULT_RATE,
        "source": "aqarmap_scrape",
    }


def _extract_from_json(data, out: dict) -> None:
    """Recursively hunt for {name, price_per_sqm} patterns in JSON blobs."""
    if isinstance(data, dict):
        name = data.get("name") or data.get("area") or data.get("district")
        price_raw = (
            data.get("price_per_sqm")
            or data.get("avg_price")
            or data.get("average_price")
            or data.get("price")
        )
        if name and price_raw:
            price = _parse_price(str(price_raw))
            if price:
                out[str(name)] = price
        for v in data.values():
            _extract_from_json(v, out)
    elif isinstance(data, list):
        for item in data:
            _extract_from_json(item, out)


# ---------------------------------------------------------------------------
# Public builder — always returns a valid map
# ---------------------------------------------------------------------------
def build_rate_map(timeout_ms: int = 25_000) -> dict:
    """
    Return a property_valuation_rate_map dict, guaranteed non-empty.
    Tries live scrape first, merges with baseline, falls back fully if needed.
    """
    scraped = None
    try:
        scraped = scrape_aqarmap(timeout_ms=timeout_ms)
    except Exception as exc:
        logger.warning("Scrape failed entirely: %s", exc)

    by_city: dict[str, float] = CAIRO_BASELINE.copy()

    if scraped and scraped.get("by_city"):
        # Live data wins; baseline fills gaps
        by_city.update(scraped["by_city"])
        source = "aqarmap_live+baseline"
    else:
        source = "baseline_only"

    logger.info("Rate map built from source=%s, districts=%d", source, len(by_city))

    return {
        "by_city": by_city,
        "by_governorate": GOVERNORATE_BASELINE.copy(),
        "default": DEFAULT_RATE,
        "source": source,
    }
