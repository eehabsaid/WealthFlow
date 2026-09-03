"""Public rate-map builder: merges live scrape results with baseline data."""

from __future__ import annotations

import logging

from .constants import CAIRO_BASELINE, GOVERNORATE_BASELINE, DEFAULT_RATE
from .district_scraper import _scrape_districts

logger = logging.getLogger(__name__)


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
