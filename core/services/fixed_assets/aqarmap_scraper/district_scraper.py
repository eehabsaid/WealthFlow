"""Live scraping loop across all known Cairo districts."""

from __future__ import annotations

import logging
import random
import time

from .constants import DISTRICT_PATHS, BASE_URL, _HEADERS
from .rsc_parsing import _decode_rsc, _extract_avg_price_data, _latest_apartment_price, _slug_matches

logger = logging.getLogger(__name__)


BLOCK_CODES = (401, 403, 429, 503)


def _failure_reason(diag: dict) -> str:
    """Why nothing live came back: not_installed | blocked (the site refused us) | network | no_data (page changed)."""
    codes = diag.get("statuses", {})
    if any(c in codes for c in BLOCK_CODES) and not codes.get(200):
        return "blocked"
    if codes.get(200):
        return "no_data"
    return "network"


def _scrape_districts(timeout: int = 20, diag: dict | None = None) -> dict[str, float]:
    """
    Fetch each district page, validate slug, return {name: price_per_sqm}.
    Districts that redirect to the city default are skipped (baseline used).
    `diag`, when given, is filled with `statuses` ({http code: count}) and, if nothing live came back, `reason`.
    """
    diag = diag if diag is not None else {}
    diag["statuses"] = {}
    try:
        import cloudscraper
    except ImportError:
        logger.warning("cloudscraper not installed — scraping skipped")
        diag["reason"] = "not_installed"
        return {}

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    results: dict[str, float] = {}

    for path, name in DISTRICT_PATHS.items():
        url = BASE_URL.format(path=path)
        try:
            r = scraper.get(url, headers=_HEADERS, timeout=timeout)
            diag["statuses"][r.status_code] = diag["statuses"].get(r.status_code, 0) + 1
            if r.status_code != 200:
                logger.debug("%-25s HTTP %d — using baseline", path, r.status_code)
                continue

            rsc = _decode_rsc(r.text)
            avg_data = _extract_avg_price_data(rsc)

            if not avg_data:
                logger.debug("%-25s no averagePriceData — using baseline", path)
                continue

            if not _slug_matches(avg_data, path):
                returned = avg_data.get("location", {}).get("slug", "?")
                logger.info(
                    "%-25s slug mismatch (got '%s') — redirect detected, using baseline",
                    path, returned,
                )
                continue

            price = _latest_apartment_price(avg_data)
            if price:
                results[name] = price
                logger.info("%-30s %10,.0f EGP/sqm  [live]", name, price)
            else:
                logger.debug("%-25s no valid price entries — using baseline", path)

        except Exception as exc:
            logger.warning("%-25s error: %s — using baseline", path, exc)

        time.sleep(random.uniform(0.5, 1.2))

    if not results:
        diag["reason"] = _failure_reason(diag)
    return results
